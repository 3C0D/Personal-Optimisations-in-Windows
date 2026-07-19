#!/usr/bin/env python3
"""
Extracteur KVS (Kernel Video Sharing) pour sites comme pervarchive.com
Approches multiples pour contourner les limitations de tezfiles.com
"""

import re
import os
import sys

import requests
from bs4 import BeautifulSoup
import http.cookiejar
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class KVSExtractor:
    """Extracteur pour sites utilisant le système KVS (Kernel Video Sharing)"""
    
    def __init__(self, cookies_file=None):
        self.session = requests.Session()
        self.cookies_file = cookies_file
        self.setup_session()
    
    def setup_session(self):
        """Configure la session avec les cookies et headers appropriés"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            self.load_cookies()
    
    def load_cookies(self):
        """Charge les cookies depuis le fichier"""
        try:
            cj = http.cookiejar.MozillaCookieJar(self.cookies_file)
            cj.load(ignore_discard=True, ignore_expires=True)
            self.session.cookies.update(cj)
            print(f"Cookies chargés depuis {self.cookies_file}")
        except Exception as e:
            print(f"Erreur lors du chargement des cookies: {e}")
    
    def extract_video_info(self, url):
        """Extrait les informations vidéo depuis une URL KVS"""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Recherche des patterns KVS communs
            video_info = self.find_video_sources(soup, response.text)
            
            if not video_info:
                # Tentative avec Selenium si nécessaire
                video_info = self.extract_with_selenium(url)
            
            return video_info
            
        except Exception as e:
            print(f"Erreur lors de l'extraction: {e}")
            return None
    
    def find_video_sources(self, soup, html_content):
        """Recherche les sources vidéo dans le HTML"""
        video_info = {
            'title': '',
            'sources': [],
            'thumbnail': ''
        }
        
        # Titre de la vidéo
        title_selectors = [
            'h1.title',
            '.video-title',
            'title',
            'h1',
            '.page-title'
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                video_info['title'] = title_elem.get_text().strip()
                break
        
        # Sources vidéo - patterns KVS
        patterns = [
            r'video_url["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'file["\']?\s*[:=]\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'src["\']?\s*[:=]\s*["\']([^"\']+\.mp4[^"\']*)["\']',
            r'video["\']?\s*[:=]\s*["\']([^"\']+)["\']',
            r'mp4["\']?\s*[:=]\s*["\']([^"\']+)["\']'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if match and match.startswith('http'):
                    video_info['sources'].append(match)
        
        # Recherche dans les balises video
        video_tags = soup.find_all('video')
        for video in video_tags:
            if video.get('src'):
                video_info['sources'].append(video['src'])
            
            sources = video.find_all('source')
            for source in sources:
                if source.get('src'):
                    video_info['sources'].append(source['src'])
        
        # Thumbnail
        thumb_selectors = [
            'video[poster]',
            '.video-thumb img',
            '.thumbnail img',
            'meta[property="og:image"]'
        ]
        
        for selector in thumb_selectors:
            thumb_elem = soup.select_one(selector)
            if thumb_elem:
                if thumb_elem.name == 'meta':
                    video_info['thumbnail'] = thumb_elem.get('content', '')
                else:
                    video_info['thumbnail'] = thumb_elem.get('poster') or thumb_elem.get('src', '')
                break
        
        # Nettoie les doublons
        video_info['sources'] = list(set(video_info['sources']))
        
        return video_info if video_info['sources'] else None
    
    def extract_with_selenium(self, url):
        """Extraction avec Selenium pour les sites avec JavaScript"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            
            # Attendre que la vidéo se charge
            wait = WebDriverWait(driver, 10)
            
            try:
                # Recherche des éléments vidéo
                video_elements = driver.find_elements(By.TAG_NAME, 'video')
                sources = []
                
                for video in video_elements:
                    src = video.get_attribute('src')
                    if src:
                        sources.append(src)
                    
                    source_elements = video.find_elements(By.TAG_NAME, 'source')
                    for source in source_elements:
                        src = source.get_attribute('src')
                        if src:
                            sources.append(src)
                
                # Titre
                title = driver.title
                
                driver.quit()
                
                if sources:
                    return {
                        'title': title,
                        'sources': list(set(sources)),
                        'thumbnail': ''
                    }
                
            except TimeoutException:
                print("Timeout lors de l'attente des éléments")
            
            driver.quit()
            
        except Exception as e:
            print(f"Erreur Selenium: {e}")
        
        return None
    
    def download_video(self, video_info, output_dir='.'):
        """Télécharge la vidéo"""
        if not video_info or not video_info['sources']:
            print("Aucune source vidéo trouvée")
            return False
        
        # Prend la première source disponible
        video_url = video_info['sources'][0]
        title = video_info['title'] or 'video'
        
        # Nettoie le nom de fichier
        filename = re.sub(r'[<>:"/\\|?*]', '_', title)
        if not filename.endswith('.mp4'):
            filename += '.mp4'
        
        filepath = os.path.join(output_dir, filename)
        
        try:
            print(f"Téléchargement de: {video_url}")
            print(f"Vers: {filepath}")
            
            response = self.session.get(video_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgrès: {percent:.1f}%", end='', flush=True)
            
            print(f"\nTéléchargement terminé: {filepath}")
            return True
            
        except Exception as e:
            print(f"Erreur lors du téléchargement: {e}")
            return False


def main():
    """Fonction principale"""
    if len(sys.argv) < 2:
        print("Usage: python kvs_extractor.py <URL> [cookies_file]")
        sys.exit(1)
    
    url = sys.argv[1]
    cookies_file = sys.argv[2] if len(sys.argv) > 2 else 'cookies.txt'
    
    extractor = KVSExtractor(cookies_file)
    
    print(f"Extraction depuis: {url}")
    video_info = extractor.extract_video_info(url)
    
    if video_info:
        print(f"Titre: {video_info['title']}")
        print(f"Sources trouvées: {len(video_info['sources'])}")
        
        for i, source in enumerate(video_info['sources']):
            print(f"  {i+1}. {source}")
        
        # Téléchargement
        if input("\nTélécharger la vidéo? (o/n): ").lower() == 'o':
            extractor.download_video(video_info)
    else:
        print("Aucune vidéo trouvée")


if __name__ == "__main__":
    main()