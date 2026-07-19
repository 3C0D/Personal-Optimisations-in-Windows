; aiMenu.ahk - Quick access menu to AI services
; Standalone script or include in other scripts with #Include aiMenu.ahk
; Hotkey: Win+Shift+I

#Requires AutoHotkey v2.0

; Hotkey definition (comment out if including in another script)
#+i:: openInAI()

; Open AI services menu with categories
openInAI() {
    aiMenu := Menu()

    ; === ASSISTANTS GÉNÉRALISTES ===
    aiMenu.Add("Claude", (*) => Run("https://claude.ai"))
    aiMenu.Add("Claude incognito", (*) => Run("https://claude.ai/new?incognito"))
    aiMenu.Add("Meta AI", (*) => Run("https://www.meta.ai/"))
    aiMenu.Add("Minimax", (*) => Run("https://agent.minimax.io/")) 
    aiMenu.Add("ChatGPT", (*) => Run("https://chatgpt.com/"))
    aiMenu.Add("Gemini", (*) => Run("https://gemini.google.com/app"))
    aiMenu.Add("Copilot", (*) => Run("https://copilot.microsoft.com"))
    aiMenu.Add("Perplexity", (*) => Run("https://www.perplexity.ai/"))
    aiMenu.Add("Grok", (*) => Run("https://grok.com/"))

    aiMenu.Add() ; Separator

    ; === ASSISTANTS SPÉCIALISÉS ===
    aiMenu.Add("Mistral", (*) => Run("https://chat.mistral.ai/chat"))
    aiMenu.Add("DeepSeek", (*) => Run("https://chat.deepseek.com/a/chat"))
    aiMenu.Add("Qwen", (*) => Run("https://chat.qwenlm.ai/"))
    aiMenu.Add("Kimi", (*) => Run("https://www.kimi.com/"))
    aiMenu.Add("GLM", (*) => Run("https://chat.z.ai/"))
    aiMenu.Add("Cici", (*) => Run("https://www.cici.com/chat/?from_logout=1"))

    aiMenu.Add() ; Separator

    ; === OUTILS SPÉCIALISÉS ===
    aiMenu.Add("Google AI Studio", (*) => Run("https://aistudio.google.com/prompts/new_chat"))
    aiMenu.Add("NotebookLM", (*) => Run("https://notebooklm.google.com/"))
    aiMenu.Add("Dia", (*) => Run("https://www.diabrowser.com/"))
    ; aiMenu.Add("Cursor", (*) => Run("https://cursor.sh"))
    aiMenu.Add("Manus", (*) => Run("https://manus.im/app"))
    ; aiMenu.Add("Fragments", (*) => Run("https://fragments.e2b.dev/"))

    aiMenu.Add() ; Separator

    ; === RECHERCHE & SYNTHÈSE ===
    aiMenu.Add("Genspark", (*) => Run("https://www.genspark.ai/"))
    aiMenu.Add("Consensus", (*) => Run("https://consensus.app/search/"))
    aiMenu.Add("Elicit", (*) => Run("https://elicit.com/"))
    aiMenu.Add("You.com", (*) => Run("https://you.com"))

    aiMenu.Add() ; Separator

    ; === MULTIMODAL ===
    aiMenu.Add("Kling AI", (*) => Run("https://klingai.com/"))

    aiMenu.Add() ; Separator

    ; === GÉNÉRATION D'IMAGES ===
    aiMenu.Add("DALL-E 3", (*) => Run("https://chatgpt.com/"))
    aiMenu.Add("Midjourney", (*) => Run("https://www.midjourney.com"))
    aiMenu.Add("Leonardo.ai", (*) => Run("https://leonardo.ai"))
    aiMenu.Add("Ideogram", (*) => Run("https://ideogram.ai"))
    aiMenu.Add("Firefly", (*) => Run("https://firefly.adobe.com"))
    aiMenu.Add("Flux", (*) => Run("https://fal.ai/"))

    aiMenu.Add() ; Separator

    ; === GÉNÉRATION VIDÉO ===
    aiMenu.Add("Runway", (*) => Run("https://runwayml.com"))
    aiMenu.Add("Pika", (*) => Run("https://pika.art"))
    aiMenu.Add("HeyGen", (*) => Run("https://www.heygen.com"))
    aiMenu.Add("Luma AI", (*) => Run("https://lumalabs.ai"))
    aiMenu.Add("Vidu", (*) => Run("https://www.vidu.com/"))
    aiMenu.Add("Wan", (*) => Run("https://wan.video/"))

    aiMenu.Add() ; Separator

    ; === VOIX & AUDIO ===
    aiMenu.Add("ElevenLabs", (*) => Run("https://elevenlabs.io"))
    aiMenu.Add("Unmute", (*) => Run("https://unmute.sh/"))

    aiMenu.Show()
}
