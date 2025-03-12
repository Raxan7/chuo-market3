universities_data = sorted([
    {
        "name": "University of Dar es Salaam",
        "colleges": [
            "College of Engineering and Technology",
            "College of Natural and Applied Sciences",
            "University of Dar es Salaam Business School",
            "College of Social Sciences",
            "College of Humanities",
            "College of Agricultural Sciences and Fisheries Technology"
        ]
    },
    {
        "name": "Sokoine University of Agriculture",
        "colleges": [
            "College of Agriculture",
            "College of Forestry, Wildlife and Tourism",
            "College of Veterinary Medicine and Biomedical Sciences",
            "College of Social Sciences and Humanities"
        ]
    },
    {
        "name": "Ardhi University",
        "colleges": [
            "School of Architecture, Construction Economics and Management",
            "School of Earth Sciences, Real Estates, Business and Informatics",
            "School of Environmental Science and Technology",
            "School of Spatial Planning and Social Sciences"
        ]
    },
    {
        "name": "Muhimbili University of Health and Allied Sciences",
        "colleges": [
            "School of Medicine",
            "School of Dentistry",
            "School of Pharmacy",
            "School of Nursing",
            "School of Public Health and Social Sciences"
        ]
    },
    {
        "name": "Mzumbe University",
        "colleges": [
            "School of Public Administration and Management",
            "School of Business",
            "School of Law",
            "School of Public Administration and Management"
        ]
    },
    {
        "name": "Nelson Mandela African Institute of Science and Technology",
        "colleges": [
            "School of Life Sciences and Bioengineering",
            "School of Computational and Communication Science and Engineering",
            "School of Materials, Energy, Water and Environmental Sciences",
            "School of Business Studies and Humanities"
        ]
    },
    {
        "name": "Tumaini University Makumira",
        "colleges": [
            "Faculty of Theology",
            "Faculty of Law",
            "Faculty of Education",
            "Faculty of Humanities and Social Sciences",
            "Faculty of Business and Economics"
        ]
    },
    {
        "name": "Open University of Tanzania",
        "colleges": [
            "Faculty of Arts and Social Sciences",
            "Faculty of Business Management",
            "Faculty of Education",
            "Faculty of Law",
            "Faculty of Science, Technology and Environmental Studies"
        ]
    },
    {
        "name": "University of Dodoma",
        "colleges": [
            "College of Humanities and Social Sciences",
            "College of Informatics and Virtual Education",
            "College of Natural and Mathematical Sciences",
            "College of Education",
            "College of Health and Allied Sciences",
            "College of Earth Sciences",
            "College of Business Studies and Law"
        ]
    },
    {
        "name": "St. Augustine University of Tanzania",
        "colleges": [
            "Faculty of Social Sciences and Communication",
            "Faculty of Business Administration",
            "Faculty of Education",
            "Faculty of Law",
            "Faculty of Engineering"
        ]
    },
    {
        "name": "Dar es Salaam Institute of Technology",
        "colleges": [
            "School of Engineering",
            "School of Business and Management",
            "School of Information and Communication Technology"
        ]
    },
    {
        "name": "International Medical and Technological University",
        "colleges": [
            "Faculty of Medicine",
            "Faculty of Nursing",
            "Faculty of Medical Laboratory Sciences"
        ]
    },
    {
        "name": "Kampala International University in Tanzania",
        "colleges": [
            "School of Health Sciences",
            "School of Education",
            "School of Business and Management"
        ]
    },
    {
        "name": "Institute of Finance Management (IFM)",
        "colleges": [
            "Faculty of Accounting, Banking and Finance",
            "Faculty of Computing, Information Systems and Mathematics",
            "Faculty of Economics and Management Sciences",
            "Faculty of Insurance and Social Protection"
        ]
    },
    {
        "name": "Mount Meru University",
        "colleges": [
            "Faculty of Theology",
            "Faculty of Education",
            "Faculty of Business Studies"
        ]
    },
    {
        "name": "Arusha Technical College",
        "colleges": [
            "School of Engineering",
            "School of Business and Management",
            "School of Information and Communication Technology"
        ]
    }
], key=lambda x: x['name'])

def display_universities_and_colleges(universities):
    for university in universities:
        print(f"University: {university['name']}")
        print("Colleges:")
        for college in university['colleges']:
            print(f"  - {college}")
        print()

def main():
    display_universities_and_colleges(universities_data)

if __name__ == "__main__":
    main()