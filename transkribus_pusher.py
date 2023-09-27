import shutil
import json
import requests
import os
import urllib3
import urllib
import xml.etree.ElementTree as ET
from credentials import transkribus_credentials,transkribus_collection_id

def transkribus_authenticate():
	auth_url="https://transkribus.eu/TrpServer/rest/auth/login"
	payload=urllib.parse.urlencode(transkribus_credentials)
	headers={'Content-Type': 'application/x-www-form-urlencoded'}
	response = requests.request("POST", auth_url, headers=headers, data=payload)
	if response.status_code!=200:
		print("error",response,response.text)
		exit()
	root = ET.fromstring(response.text)
	sessionId=[c.text for c in root if c.tag=='sessionId'][0]
	headers['Cookie']='='.join([ 'JSESSIONID',sessionId])
	return headers

def transkribus_create_document(docdict,auth_headers):
	auth_headers['Content-Type']='application/json'
	url='https://transkribus.eu/TrpServer/rest/uploads?collId='+transkribus_collection_id
	print(url)
	resp=requests.request("POST",url,headers=auth_headers,data=json.dumps(docdict))
	status_code=resp.status_code
	if status_code!=200:
		print("ERROR---->",resp)
		exit()
	root = ET.fromstring(resp.text)
	print('document creation response:')
	for c in root:
		print("\t",c.tag,c.text)
	uploadId=[c.text for c in root if c.tag=='uploadId'][0]
	return uploadId,root

def getpagefilename(pagedata):
	pagenumber=page['pageNr']
	if page['fileName'] is None:
		filename=str(page['page_pk'])+'.jpg'
	else:
		filename=page['fileName']
	return filename

def push_iiif_image(tmp_filepath,page,headers,upload_id,xml_root):
	print("filepath",tmp_filepath)
	for child in xml_root:
		if child.tag=='pageList':
			for pages in child:
				for pagenode in pages:
					if pagenode.tag=='fileName' and pagenode.text in tmp_filepath:
						this_page_xml=pages
						filename=pagenode.text
						print("filename-->",filename)
	
	print(ET.tostring(this_page_xml, encoding='unicode'))
	
	
	del(headers['Content-Type'])
# 	headers['Content-Type']='multipart/form-data'
	print(headers)
	url='https://transkribus.eu/TrpServer/rest/uploads/'+upload_id
	print(url)
	files=[('img',('8151.jpg',open('tmp/8151.jpg','rb'),'image/jpeg'))]
	resp=requests.put(
		url,
		files=files,
		data={},
		headers=headers
	)
	print(resp)
	print(resp.text)
	
#        {
#          "fileName": null,
#          "page_pk": 8151,
#          "pageNr": 1,
#          "docpagenumber": 1,
#          "uri": "https://quod.lib.umich.edu/cgi/t/text/api/image/shelburne:shelburne.0043.001:00000001/full/max/0/default.jpg"
#       },


def download_iiif_image(page):
	iiif_url=page['uri']
	img_filename=getpagefilename(page)
	tmp_filepath=os.path.join('tmp/',img_filename)
	
	print('fetching',img_filename,iiif_url)
	r = requests.get(iiif_url, stream=True)
	if r.status_code == 200:
		with open(tmp_filepath, 'wb') as f:
			r.raw.decode_content = True
			shutil.copyfileobj(r.raw, f)
		return tmp_filepath
	else:
		print('FAILED ON',img_filename,iiif_url)
		exit()






##############################################

#LOAD THE JSON DATA FOR THE DOCS AND PAGES
d=open('documents_pages.json','r')
t=d.read()
d.close()

documents=json.loads(t)


#THEN AUTHENTICATE 
auth_headers=transkribus_authenticate()


#THEN RUN THROUGH THE DOCUMENTS (DIFFERENTIATED BY SHORTREFS) ONE BY ONE
for shortref in documents:
	document_json={
		"md": {
			"title": shortref
		},
        "pageList": {
        	"pages": []
        }
    }
    
    #create the upload handler on the transkribus side
	for page in documents[shortref]:
#        {
#          "fileName": null,
#          "page_pk": 8151,
#          "pageNr": 1,
#          "docpagenumber": 1,
#          "uri": "https://quod.lib.umich.edu/cgi/t/text/api/image/shelburne:shelburne.0043.001:00000001/full/max/0/default.jpg"
#       },
		pagenumber=page['pageNr']
		filename=getpagefilename(page)
		page_json={
			"pageNr":pagenumber,
			"fileName":filename
		}
		document_json['pageList']['pages'].append(page_json)
	print('creating doc',shortref)
	uploadId,xml_root=transkribus_create_document(document_json,auth_headers)
	print("----\nuploadId---->",uploadId)
	
	#now download the file and push it to transkribus
	for page in documents[shortref]:
		tmp_filepath=download_iiif_image(page)
		
		push_iiif_image(tmp_filepath,page,auth_headers,uploadId,xml_root)
	
	exit()