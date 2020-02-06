import numpy as np
import cv2
import pickle
import boto3
import uuid
import paho.mqtt.client as mqtt
import flask
#!flask/bin/python
from flask import Flask
from flask import request
import jsonify
app = Flask(__name__)

REGISTER_TOPIC = "faceEvent/registered/faceID/"
BUCKET = "face-event"  # This is the bucket where the face your trying to match lives
COLLECTION = "faces"
SOURCE_FILENAME = 'face.jpg'
face_cascade = cv2.CascadeClassifier(
	'cascades/data/haarcascade_frontalface_alt2.xml')
eye_cascade = cv2.CascadeClassifier('cascades/data/haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier('cascades/data/haarcascade_smile.xml')



recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("./recognizers/face-trainner.yml")

# labels = {"person_name": 1}
# with open("pickles/face-labels.pickle", 'rb') as f:
# 	og_labels = pickle.load(f)
# 	labels = {v: k for k, v in og_labels.items()}

cap = cv2.VideoCapture(0)
threshold = 70
maxFaces = 1
client = boto3.client('rekognition', 'us-east-1')
print('client init done')

def on_publish(mqtt_client, userdata, mid):
    print("mid: "+str(mid))

mqtt_client = mqtt.Client()
mqtt_client.on_publish = on_publish
mqtt_client.connect("api.akriya.co.in", 1883)
mqtt_client.loop_start()

def upload_to_aws(local_file, bucket, s3_file):
	s3 = boto3.client('s3')

	try:
		s3.upload_file(local_file, bucket, s3_file)
		print("Upload Successful")
		return True
	except FileNotFoundError:
		print("The file was not found")
		return False
	except NoCredentialsError:
		print("Credentials not available")
		return False

def add_faces_to_collection(bucket, photo, collection_id):
	client = boto3.client('rekognition', 'us-east-1')
	response = client.index_faces(CollectionId=collection_id,
                               Image={'S3Object': {
                                   'Bucket': bucket, 'Name': photo}},
                               ExternalImageId=photo,
                               MaxFaces=1,
                               QualityFilter="AUTO",
                               DetectionAttributes=['ALL'])

	print('Results for ' + photo)
	print('Faces indexed:')
	for faceRecord in response['FaceRecords']:
		 print('  Face ID: ' + faceRecord['Face']['FaceId'])
		 print('  Location: {}'.format(faceRecord['Face']['BoundingBox']))

	print('Faces not indexed:')
	for unindexedFace in response['UnindexedFaces']:
		print(' Location: {}'.format(
			unindexedFace['FaceDetail']['BoundingBox']))
		print(' Reasons:')
		for reason in unindexedFace['Reasons']:
			print('   ' + reason)
	return len(response['FaceRecords'])

def detect(src):
    print('starting detect')
    id = uuid.uuid1()
    KEY = id.hex + ".jpg"
    uploaded = upload_to_aws(src, BUCKET,KEY)
    if(uploaded):
        response = client.search_faces_by_image(CollectionId=COLLECTION,
                                            Image={'S3Object': {
                                                'Bucket': BUCKET, 'Name': KEY}},
                                            FaceMatchThreshold=threshold,
                                            MaxFaces=maxFaces)
        faceMatches = response['FaceMatches']
        print('Matching faces ', faceMatches)
        if len(faceMatches) < 1 :
            print('Empty found')
        else :
            print ('Match Found')
            return True
    return False


def register(src):
    print(src)
    if detect(src):
        print('bhap')
        return 'Already Registered'
    else:
        print('Attempting to save new face')
        id = uuid.uuid1()
        KEY = id.hex + ".jpg"
        uploaded = upload_to_aws(src, BUCKET,KEY)
        add_faces_to_collection(BUCKET, KEY, COLLECTION)
        print('added image index')
        return str(KEY)
        

@app.route('/')
def index():
    return "Hello, World!"

# http://localhost:5000/api/v1.0/register
@app.route('/api/v1.0/register', methods=['POST'])
def create_task():
    print(request.json)
    print(request.form.get('src'))
    if not request.form.get('src'):
        # abort(400)
        print('bla')
        response = 'No src attribute'
    else:    
        # response
        # response = register(request.json.get('src'))
        # register(request.form.get('src'))
        response = 'adc3c0ce20c511eaab4bf079600d216c.jpg'

    return response, 201

if __name__ == '__main__':
    app.run(debug=True)