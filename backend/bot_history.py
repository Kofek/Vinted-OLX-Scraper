import os


def load_history(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, "r", encoding="utf-8") as file:
        return set(line.strip() for line in file)


def save_link(link, file_path):
    directory = os.path.dirname(file_path)

    # Jeśli podano folder i ten folder nie istnieje, stwórz go automatycznie
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    with open(file_path, "a", encoding="utf-8") as file:
        file.write(link + "\n")
