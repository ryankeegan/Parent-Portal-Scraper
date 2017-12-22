import requests
from lxml import html
import sys
import re

username = sys.argv[1]
password = sys.argv[2]
studentName = sys.argv[3]
coursesReturned = 8	#Number of courses returned to the end user

payload = {	#Keys for connecting to Aeries
	"checkCookiesEnabled": "true",
	"checkSilverlightSupport": "true",
	"checkMobileDevice": "false",
	"checkStandaloneMode": "false",
    "checkTabletDevice": "false",
	"portalAccountUsername": username,
	"portalAccountPassword": password,
    "submit": ""
}

session_requests = requests.session()

login_url = "http://parents.vistausd.org/LoginParent.aspx"
result = session_requests.get(login_url)
tree = html.fromstring(result.text)


result = session_requests.post(
	login_url,
	data = payload,
	headers = dict(referer=login_url)
)

url = 'http://parents.vistausd.org/Default.aspx'
result = session_requests.get(
	url,
	headers = dict(referer = url)
)
tree = html.fromstring(result.content)
students = tree.xpath('//div[@id="Sub_7"]/a') #Stores all a tags in 'Change Student' drop down on Parent Portal

for student in students:
	if(studentName.split(" ")[0] in student.text_content()): #Find best fit for student's first name
		url = 'http://parents.vistausd.org/' + student.attrib['href']; #Visit url to change student session to best fit
		break;

result = session_requests.get(
	url,
	headers = dict(referer = url)
)

#Parse transcripts once student has been selected
url = 'http://parents.vistausd.org/Transcripts.aspx'
result = session_requests.get(
	url,
	headers = dict(referer = url)
)
tree = html.fromstring(result.content)
courseInfo = tree.xpath('//td[@class="Data"]/text()') #Only stores tags that follow '<td class="Data"' pattern.
#If this program stops working this is likely the culprit. Load the transcripts page and see if the tags have changed.
studentInfo = tree.xpath('//span[@class="list-data"]/text()')
courseIDs = [] #Stores course IDs
grades = [] #Stores grades

def is_ascii(text): #Determines whether or not a character is ASCII. Used to filter contents that meet the 4 character limit but aren't a course id
    if isinstance(text, unicode):
        try:
            text.encode('ascii')
        except UnicodeEncodeError:
            return False
    else:
        try:
            text.decode('ascii')
        except UnicodeDecodeError:
            return False
    return True

def score(x): #Maps each grade to a point value that is used when computing eligibility. A '-1' makes you ineligible for CSF
	return { #This doesn't account for honours. That is done in eligibility.php
		'A': 3,
		'B': 1,
		'C': 0,
		'D': -1,
		'F': -1
	}.get(x, -1)

for element in courseInfo:
	if(len(element) == 4 and "." not in element and "/" not in element and is_ascii(element)):
		#Filters Course IDs
		courseIDs.append(element)
	if(("A" in element or "B" in element or "C" in element or "D" in element or "F" in element) and ((len(element) == 2 and ("-" in element or "+" in element)) or len(element) == 1)):
		#Filters Grades
		grades.append(element)

#Begin formatting JSON that will be returned
print("[")
for x in range (0, coursesReturned):
	print("{\"course_id\":\"" + courseIDs[x] + "\"" + ", \"grade\":" + str(score(grades[x][:1])) + "}")
	if(x<(coursesReturned-1)):
		print(",")
print("]")

#What is printed to the console is decoded and used as a 2D array in eligibility.php
#The first key is a normal index (0, 1, 2, etc.) and the second key is either the grade or course id (associative)
#Ex: $array[0]['grade']		Where 0 refers to the first entry and grade refers to the point value for the course


#Return student ID to verify student's identity
for element in studentInfo:
	if(len(element) == 9 and not re.search('[a-zA-Z]', element) and "/" not in element):
		print("*" + element)								#'*' is for easy seperation of the student id and JSON

#Find duplicate courses
gradeIndex = 0
coursesUnique = [] #First semester taking course
coursesDuplicate = [] #Second semester taking course (2 semesters = 1 term)
coursesRetake = [] #Third semester taking course (indicates retake)
while(gradeIndex < len(grades)): #Each course should having a matching grade (fix for garbled course data at the end of course ids array)
	if(not courseIDs[gradeIndex] in coursesUnique): #First time taking course
		coursesUnique.append(courseIDs[gradeIndex])
	elif(not courseIDs[gradeIndex] in coursesDuplicate): #There can be duplicate courses (same course over two semesters)
		coursesDuplicate.append(courseIDs[gradeIndex])
	elif(not courseIDs[gradeIndex] in coursesRetake): #More than two grades for the same course indicates retake
		coursesRetake.append(courseIDs[gradeIndex])
	gradeIndex += 1


#Return duplicate courses in the form of JSON
print("^{") #'^' is for easy seperation of duplicate courses JSON and the student id
x = 0
for course in coursesRetake:
	print("\"course_id\":\"" + course + "\"")
	if(x<(len(coursesRetake)-1)):
		print(",")
	x += 1
print("}")
