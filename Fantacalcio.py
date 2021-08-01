
'''
urls:
quotazioni:
https://www.fantacalcio.it//Servizi/Excel.ashx?type=0&r=1&t=1614489243000
https://www.fantacalcio.it/quotazioni-fantacalcio

voti:
https://www.fantacalcio.it/Servizi/Excel.ashx?type=2&r=1&t=1614489243000&s=2020-21
https://www.fantacalcio.it/statistiche-serie-a/2020-21/fantacalcio/medie
'''

import warnings
warnings.filterwarnings("ignore")
import pandas as pd
import os
import wget, requests

def quotazioni():
    url='https://www.fantacalcio.it/quotazioni-fantacalcio'
    #www.fantacalcio.it//Servizi/
    req=requests.get(url).text
    req=[i for i in req.splitlines() if 'www.fantacalcio.it//Servizi/' in i][0]
    # req=req.replace('            location.href = "//','https://').replace('"','')
    req=req.replace('            location.href = "','').replace('"','')
    try:os.remove('./Quotazioni_Fantacalcio_Ruoli_Fantagazzetta2.xlsx')
    except: pass
    wget.download(req,out='./Quotazioni_Fantacalcio_Ruoli_Fantagazzetta2.xlsx')
    print('\n Download delle quotazioni completato\n')
    return True

def scarica(stagione):
    url='https://www.fantacalcio.it/statistiche-serie-a/'+stagione+'/fantacalcio/medie'
    #            location.href = "//www.fantacalcio.it/Servizi/
    req=requests.get(url).text
    req=[i for i in req.splitlines() if 'www.fantacalcio.it/Servizi/' in i and stagione in i][0]
    req=req.replace('            location.href = "','').replace('"','')
    try:os.remove('./Statistiche_Fantacalcio_'+stagione+'_Fantagazzetta.xlsx')
    except: pass
    wget.download(req,out='./Statistiche_Fantacalcio_'+stagione+'_Fantagazzetta.xlsx')
    print("\nDataset stagione {} completato.".format(stagione))
    return True

def prune(dataset):
	temp=pd.DataFrame()
	temp['Nome']=dataset['Nome']
	temp['Pg']=dataset['Pg']
	temp['Mf']=dataset['Mf']
	return temp
	
if __name__=='__main__':
	manuale=False
	scelta=input("Inserire stagione nel formato yyyy-yy (es. 2021-22): ")
	if scelta=='': 
		scelta='2021-22'

	anno1=int((scelta.split('-'))[0])
	scelta2=str(anno1-1)+'-'+str(anno1%2000)
	scelta3=str(anno1-2)+'-'+str(anno1%2000-1)
	print("Scaricando le statistiche di ",scelta,scelta2,scelta3)
	scelta1=scelta #non ho sbatta di rinominare
	try:
		quotazioni()
		scarica(scelta1)
		scarica(scelta2)
		scarica(scelta3)
	except Exception as e: 
		print("\nErrore nei download\n",e)
		exit(0)

	dataset_quotazioni = pd.read_excel("./Quotazioni_Fantacalcio_Ruoli_Fantagazzetta2.xlsx",header = 1,engine='openpyxl')

	#debug 
	list(dataset_quotazioni.columns.values)
	#['Id', 'R', 'Nome', 'Squadra', 'Qt. A', 'Qt. I', 'Diff.']

	#droppo le colonne che non voglio utilizzare nel dataset finale
	dataset_quotazioni = dataset_quotazioni.drop('Id',1)
	dataset_quotazioni = dataset_quotazioni.drop('Diff.',1)
	#debug
	#list(dataset_quotazioni.columns.values)
	#['R', 'Nome', 'Squadra', 'Qt. A', 'Qt. I']

	dataset_statistiche1 = pd.read_excel("./Statistiche_Fantacalcio_"+scelta3+"_Fantagazzetta.xlsx",header = 1,engine='openpyxl')
	dataset_statistiche2 = pd.read_excel("./Statistiche_Fantacalcio_"+scelta2+"_Fantagazzetta.xlsx",header = 1,engine='openpyxl')
	dataset_statistiche3 = pd.read_excel("./Statistiche_Fantacalcio_"+scelta1+"_Fantagazzetta.xlsx",header = 1,engine='openpyxl')

	calciatorioggi=list(dataset_statistiche3['Nome']+'/'+dataset_statistiche3['Squadra'])
	calciatoriold=list(dataset_statistiche2['Nome']+'/'+dataset_statistiche2['Squadra'])
	calciatoriold_dict = dict(zip(dataset_statistiche2['Nome'].to_list(), dataset_statistiche2['Squadra'].to_list()))
	giveatry=[i.split('/')[0] for i in calciatorioggi if i not in calciatoriold]

	#debug 
	list(dataset_statistiche1.columns.values)
	#['Id', 'R', 'Nome', 'Squadra', 'Pg', 'Mv', 'Mf', 'Gf', 'Gs', 'Rp', 'Rc', 'R+', 'R-', 'Ass', 'Asf', 'Amm', 'Esp', 'Au']
	#nome, partite_giocate,media_fantacalcio
	#['Nome', 'Pg', 'Mf']
	dataset_statistiche1=prune(dataset_statistiche1)
	dataset_statistiche2=prune(dataset_statistiche2)
	dataset_statistiche3=prune(dataset_statistiche3)

	df1 =pd.DataFrame(dataset_quotazioni)
	df2 =pd.DataFrame(dataset_statistiche1)
	df3 =pd.DataFrame(dataset_statistiche2)
	df4 =pd.DataFrame(dataset_statistiche3)

	dataset = df1.merge(df2,on="Nome").merge(df3,on="Nome").merge(df4,on="Nome")
	#result = dataset.sort_values(by='Qt. I')

################# core 
	media_giocatori = [];
	for index, row in dataset.iterrows():
		if  row.Pg_x > 0 or row.Pg_y > 0:	
			media_pesata_partite_giocate = (row.Pg_x/38 * row.Mf_x)*0.20 + (row.Pg_y/38 * row.Mf_y)*0.80 
			media_giocatori.append(media_pesata_partite_giocate)
		else:
			media_giocatori.append(0)

	dataset["mediaGiocatori"] = media_giocatori
	media = []

	for index, row in dataset.iterrows():
		if  row.mediaGiocatori > 0:	 
			media.append(row.mediaGiocatori/row["Qt. I"])
		else:
			media.append(0)
	dataset["media"] = media
	#result = dataset.sort_values(by="media")

	giocatemax=0
	for index, row in dataset.iterrows():
			if  row.Pg > giocatemax: giocatemax=row.Pg
		
	print("in questa stagione sono state disputate ",giocatemax," partite")

	if giocatemax==0:giocatemax=1 #se il campionato non è iniziato evito la divisione per zero

	media_giocatori = [];
	for index, row in dataset.iterrows():
		if  row.Pg > 0:	 
			media_pesata_partite_giocate = (row.Pg_x/38 * row.Mf)*0.20 + (row.Pg_y/38 * row.Mf)*0.40 + (row.Pg/giocatemax * row.Mf)*0.40
			media_giocatori.append(media_pesata_partite_giocate)
		else:
			media_giocatori.append(0)

	dataset["mediaGiocatori_today"] = media_giocatori

	media = []

	for index, row in dataset.iterrows():
		if  row.mediaGiocatori_today > 0:	 
			media.append(row.mediaGiocatori/row["Qt. I"])
		else:
			media.append(0)
	dataset["media_today"] = media


	prob=[]
	for index, row in dataset.iterrows():
		if int(row.Pg_y) <= int(row.Pg_x):	 ## rivedere calcolo
			if round(int(row.Pg_y)/38*100-(int(row.Pg_x+1)/int(row.Pg_y+1))) < 0 : prob.append(round(-1/2*(int(row.Pg_y)/38*100-(int(row.Pg_x+1)/int(row.Pg_y+1)))))
			else : prob.append(round(int(row.Pg_y)/38*100-(int(row.Pg_x+1)/int(row.Pg_y+1))))#/38*100))
		else:
			if round(int(row.Pg_y)/38*100+(int(row.Pg_y)/int(row.Pg_x+1))) > 100: prob.append(99.5)
			else : prob.append(round(int(row.Pg_y)/38*100+(int(row.Pg_y)/int(row.Pg_x+1))))#/38*100)/2)

	dataset["Probabile titolarità futura (occhio se il giocatore ha cambiato squadra)"] = prob

	prob=[]
	for index, row in dataset.iterrows():
		if row.Nome in giveatry:	 
			prob.append('Y - ex '+calciatoriold_dict[row.Nome])
		else:
			prob.append('N')

	dataset["Squadra Nuova"] = prob

	total = []
	for index, row in dataset.iterrows():
		if  row.mediaGiocatori > 0:	 
			total.append(row.mediaGiocatori*row.media*row['Mf_y'])
		else:
			total.append(0)

	dataset["convenienza_inizio_campionato (considera solo le due annate precedenti concluse)"] = total


	total = []
	for index, row in dataset.iterrows():
		if  row.mediaGiocatori > 0:	 
			total.append(row.mediaGiocatori_today*row.media_today*row['Mf'])
		else:
			total.append(0)

	dataset["convenienza_today"] = total
	if giocatemax < 2: result = dataset.sort_values(by="convenienza_inizio_campionato (considera solo le due annate precedenti concluse)",ascending=False)
	else: result = dataset.sort_values(by="convenienza_today",ascending=False)
	#drop mediaGiocatori	media	mediaGiocatori_today	media_today

	result = result.drop('mediaGiocatori',1) 
	result = result.drop('media',1) 
	result = result.drop('mediaGiocatori_today',1) 
	result = result.drop('media_today',1) 

########### generating output ##################

	try:os.mkdir("./res")
	except:pass
	print("Generating xls...")
	result.to_excel('./res/result.xls')

	df = result[result["R"] == "A"]
	df.to_excel('./res/dataset_A_.xls')

	df = result[result["R"] == "C"]
	df.to_excel('./res/dataset_C_.xls')

	df = result[result["R"] == "D"]
	df.to_excel('./res/dataset_D_.xls')

	df = result[result["R"] == "P"]
	df.to_excel('./res/dataset_P_.xls')
	input("Premere qualsiasi tasto per terminare")