import requests
import json
from credentials import auth_token,voyages_api_baseurl
import os
import time

url = voyages_api_baseurl

# We already did 'DOCP Huntington 57 21'

doc_collections={
	'AP':[
		'AP Clement 43',
		'AP Clement 44'
	],
	'DOCP':[
		'DOCP Huntington 57 17',
		'DOCP Huntington 57 18',
		'DOCP Huntington 57 19',
		'DOCP Huntington 57 21'
	]
}

headers = {
  'Authorization': auth_token
}

results_per_page=20

def documents_pages_update(shortref,pagelist):
	dpfname='documents_pages.json'
	if os.path.exists(dpfname):
		d=open(dpfname,'r')
		t=d.read()
		d.close()
		docspages=json.loads(t)
	else:
		docspages={}
	docspages[shortref]=pagelist
	
	d=open(dpfname,'w')
	t=d.write(json.dumps(docspages,indent=3))
	d.close()


for doc_collection in doc_collections:
	print("+++++++++++++++++++")
	print('DOC COLLECTION-->',doc_collection)
	short_refs=doc_collections[doc_collection]
	for short_ref in short_refs:
		shortrefpagelist=[]
		shortrefpagenumber=1
		print("SHORT REF-->",short_ref)
		#first, get pagecount
		print('fetching total results')
		payload = {
			'short_ref': short_ref,
			'results_per_page':results_per_page
		}
		response = requests.request("POST", url, headers=headers, data=payload)
		sc=response.status_code
# 		print(sc)
		if sc==200:
			total_results_count=int(response.headers['total_results_count'])
			total_pages=total_results_count/results_per_page
			if int(total_pages)<total_pages:
				total_pages=int(total_pages)+1
			else:
				total_pages=int(total_pages)
		for pagenumber in range(1,total_pages+1):
			print("page number",pagenumber)
			payload['results_page']=pagenumber
			response = requests.request("POST", url, headers=headers, data=payload)
			if sc==200:
				j=json.loads(response.text)
# 				print('number of results on this page:',len(j))
				for source in j:
					source_page_connections=source['page_connection']
					
					docpagenumber=1
					for source_page_connection in source_page_connections:
						source_page=source_page_connection["source_page"]
						iiif_baseimage_url=source_page["iiif_baseimage_url"]
						image_filename=source_page["image_filename"]
						##If michigan has filenames, I don't -- will have to use pk+'.jpg' -- argh
						page_pk=source_page["id"]
						docpagedict={
							"fileName":image_filename,
							"page_pk":page_pk,
							"pageNr":shortrefpagenumber,
							"docpagenumber":docpagenumber,
							'uri':iiif_baseimage_url,
						}
						docpagenumber+=1
						shortrefpagenumber+=1
						shortrefpagelist.append(docpagedict)
			else:
				print("---------->FAILED")
		documents_pages_update(short_ref,shortrefpagelist)
	print("+++++++++++++++++++")
