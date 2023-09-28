import shutil
import json
import requests
import os
import time
import sys
import urllib3
import urllib
import xml.etree.ElementTree as ET
from credentials import transkribus_credentials,transkribus_collection_id
from multiprocessing import Pool,TimeoutError
import numpy as np
from optparse import OptionParser, Option, OptionValueError

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
	print(json.dumps(docdict,indent=2))
	resp=requests.request("POST",url,headers=auth_headers,data=json.dumps(docdict))
	status_code=resp.status_code
	if status_code!=200:
		print("ERROR---->",resp)
		exit()
	root = ET.fromstring(resp.text)
# 	print('document creation response:')
# 	for c in root:
# 		print("\t",c.tag,c.text)
	uploadId=[c.text for c in root if c.tag=='uploadId'][0]
	return uploadId,root

def getpagefilename(pagedata):
	#PAGE FILENAMES IN THIS TRANSKRIBUS UPLOAD WILL ALL BE THE PRIMARY KEY FOR THAT PAGE IN THE DATABASE
	filename=str(pagedata['page_pk'])+'.jpg'
	return filename

def push_iiif_image(tmp_filepath,page,headers,upload_id,xml_root):
	for child in xml_root:
		if child.tag=='pageList':
			for pages in child:
				for pagenode in pages:
					if pagenode.tag=='fileName' and pagenode.text in tmp_filepath:
						this_page_xml=pages
						filename=pagenode.text
	if 'Content-Type' in headers:
		del(headers['Content-Type'])
	url='https://transkribus.eu/TrpServer/rest/uploads/'+upload_id
	files=[('img',(filename,open(tmp_filepath,'rb'),'image/jpeg'))]
	error_counter=0
	print("pushing-->",filename)
	while error_counter<5:
		try:
			resp=requests.put(
					url,
					files=files,
					data={},
					headers=headers
				)
			sc=resp.status_code
		except:
			sc="not good"
		if sc == 200:
			os.remove(tmp_filepath)
			break
		else:
			error_counter+=1
			print('FAILED ON',tmp_filepath)
			waitseconds=2**error_counter
			print('waiting',waitseconds,'seconds')
			time.sleep(waitseconds)

def download_iiif_image(page):
	iiif_url=page['uri']
	img_filename=getpagefilename(page)
	tmp_filepath=os.path.join('tmp/',img_filename)
	if iiif_url in ["None","",None]:
		return None
	print('fetching',img_filename,iiif_url)
	error_counter=0
	while error_counter<5:
		r = requests.get(iiif_url, stream=True)
		if r.status_code == 200:
			with open(tmp_filepath, 'wb') as f:
				r.raw.decode_content = True
				shutil.copyfileobj(r.raw, f)
			return tmp_filepath
			break
		else:
			error_counter+=1
			print('FAILED ON',img_filename,iiif_url)
			waitseconds=2**error_counter
			print('waiting',waitseconds,'seconds')
			time.sleep(waitseconds)

def pages_to_transkribus(work_and_params):
	
	pages_batch,params=work_and_params
	auth_headers,uploadId,xml_root=params
	
	for page in pages_batch:
		tmp_filepath=download_iiif_image(page)
		if tmp_filepath is not None:
			push_iiif_image(tmp_filepath,page,auth_headers,uploadId,xml_root)

##############################################

#LOAD THE JSON DATA FOR THE DOCS AND PAGES

#"Allow user to specify number of processes"

parser = OptionParser()
parser.add_option("--shortref", action="store", type="str", dest="shortref",default=None)
parser.add_option("--workers", action="store", type="int", dest="workers",default=1)
(options, args) = parser.parse_args()
shortref=options.shortref
workers=options.workers

d=open('documents_pages.json','r')
t=d.read()
d.close()
documents=json.loads(t)
#"Allow user to specify a single shortref to push up"
if shortref:
	if shortref in documents:
		documents={shortref:documents[shortref]}
	else:
		print("error. shortref",shortref,"not in documents")
		exit()

if __name__ == '__main__':
	
	print("running on the following shortrefs:",list(documents.keys()))
	
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
	
		auth_headers=transkribus_authenticate()
	
		#create the upload handler on the transkribus side
		for page in documents[shortref]:
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
		doc_pages=np.array(list(documents[shortref]))
		workbatches=list(np.array_split(doc_pages,workers))
		workbatches_and_params=[[workbatch,[auth_headers,uploadId,xml_root]] for workbatch in workbatches]
		for i in workbatches_and_params:
			print(i[0],i[1])
# 		exit()
		with Pool(processes=workers) as pool:
			pool.map(pages_to_transkribus,workbatches_and_params)