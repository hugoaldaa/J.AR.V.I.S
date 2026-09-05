from backend.memoria.obsidian import search_vault


results = search_vault("Ollama")


if not results:
    print("No se ha encontrado nada.")
else:
    for result in results:
        print("Archivo:", result["file"])
        print(result["content"])
        print("-" * 50)