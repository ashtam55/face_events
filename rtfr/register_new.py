import numpy as np
import cv2
import pickle
import boto3
import uuid
import paho.mqtt.client as mqtt

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
    if detect(src):
        print('bhap')
    else:
        print('Attempting to save new face')
        id = uuid.uuid1()
        KEY = id.hex + ".jpg"
        uploaded = upload_to_aws(src, BUCKET,KEY)
        add_faces_to_collection(BUCKET, KEY, COLLECTION)
        mqtt_client.publish(REGISTER_TOPIC,str(KEY), qos=0)   
        print('added image index')

while(True):
    ret, frame = cap.read()  # we got image
    faces = face_cascade.detectMultiScale(frame, 1.6, 6)
    # now see if there are faces
    if(len(faces) != 0):
        print("Psst! "+str(len(faces))+" peep(s) at the door!")
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
            roi_color = frame[y:y+h, x:x+w]
            img_item = "face.jpg"
            cv2.imwrite(img_item, roi_color)
            register(img_item)
    cv2.imshow('frame', frame)

    if cv2.waitKey(20) & 0xFF == ord('q'):
        break 
        # collectionId='faces'
        # faces=[]
        # faces.append("9f64b54e-5eb9-4ad7-997a-9e35b6ce83a8")

        # client=boto3.client('rekognition','us-east-1')

        # response=client.delete_faces(CollectionId=collectionId,
        #                         FaceIds=faces)

        # print(str(len(response['DeletedFaces'])) + ' faces deleted:') 							
        # for faceId in response['DeletedFaces']:
        #     print (faceId)  
        
# When everything done, release the capture
cap.release()
cv2.destroyAllWindows()