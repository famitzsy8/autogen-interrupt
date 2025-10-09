def get_cogmaster_professors():
    professors = {
        "Philosophy Major": "Valeria Giardino (CNRS)",
        "Social Sciences Major": "Nicolas Baumard (CNRS & ENS)",
        "Linguistics Major": ["Pascal Amsili (Université de Paris)", "Maria Giavazzi (ENS-PSL)"],
        "Cognitive Psychology Major": "Jérôme Sackur (EHESS)",
        "Cognitive Neuroscience Major": ["Daniel Pressnitzer (CNRS)", "Thomas Andrillon (Inserm)"],
        "Modelling Major": ["Jean-Pierre Nadal (EHESS)", "Mehdi Khamassi (CNRS)"],
        "Cognitive Engineering & Society Major": ["Valérien Chambon (CNRS)", "Emmanuel Dupoux (EHESS)"]
    }

    for major, faculty in professors.items():
        if isinstance(faculty, list):
            faculty = ", ".join(faculty)
        print(f"{major}: {faculty}")

if __name__ == "__main__":
    get_cogmaster_professors()
