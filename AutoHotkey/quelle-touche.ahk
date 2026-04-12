#Requires AutoHotkey v2.0


MsgBox "Appuie sur OK puis clique une touche"

ih := InputHook("L1 V")
ih.KeyOpt("{All}", "SE")
ih.Start()
ih.Wait()

vk := ih.EndKey
MsgBox "Touche : " . vk . "`nSC: " . GetKeySC(vk), "Résultat"