# importing the requests library 
import requests 

# api-endpoint 
URL = "http://localhost:5000/api/v1.0/register"

# location given here 
location = "delhi technological university"

# defining a params dict for the parameters to be sent to the API 
data = {'src':location} 

# sending get request and saving the response as response object 
r = requests.post(url = URL, data = data) 

# extracting data in json format 
data = r
print(data)
# printing the output 
# print("Data:%s\n"
# 	%(data)) 
