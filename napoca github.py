
from urllib.error import HTTPError
import pandas as pd
import numpy as np
from urllib.request import urlopen
from bs4 import BeautifulSoup as bs
import re
import csv
import time
import requests
import os
import pickle
import copy

from pygeocoder import Geocoder
from pygeolib import GeocoderError


def anunt(link, printare = False):
    '''
    --------------CONEXIUNEA------------
    aici realizam conexiunea la site
    '''
    
    try:
        html = urlopen(link)
    except HTTPError as e: #in caz ca nu poate deschide anuntul
        print(link)
        return None       
    except requests.ConnectionError as e: #am primit eroare de conectare asa ca am pus sa incerce inca o data dupa 120 de secunde
        time.sleep(120)
        print(link)
        print('probleme la conexiune')
        anunt(link)
    anunt= bs(html.read(), 'html.parser')  #deschidem cu beautiful soup link-ul
    
    '''
    --------------TITLUL SI PRETUL------------
    extragem titlul si pretul
    in caz ca nu le putem extrage, functia va returna None si vom printa link-ul
    pentru ca nu aflam niste informatii esentiale
    '''
    
    try:
        titlu_anunt = anunt.find('div', {'id':'content'}).h1.text
    except AttributeError:
        print(link)
        print('nu am putut extrage titlul')
        return None
    
    
    try:
        pret = anunt.find('div', {'class':'price'}).text  #titlul era cu h1
        pret = re.sub(r'\D', '', pret)
        #titlu_anunt = titlu_anunt
    except AttributeError: #in caz ca nu gaseste dupa codul html sa nu mai incerce
        print('nu am putut extrage pretul')
        print(link)
        return None
    
    
    '''
    --------------DESCRIEREA SAU DATELE DESPRE APARTAMENT------------
    descrierea este textul care descrie apartamentul intr-un text, ca o poveste
    '''
    
    
    try:
        descriere_text = anunt.find('p', {'class':'description'}).get_text() #pretul era intr-un div cu id-ul respectiv
        descriere_text = descriere_text.replace('\n', '')
        descriere_text = descriere_text.replace('\r', '')
        descriere_text = descriere_text.replace('\t', '')
    except AttributeError:
        print(link)
        print('probleme cu descrierea')
        return None
    #print(descriere_text)
    
    
    '''
    --------------DATE APARTAMENT------------
    datele tabelare despre apartament sunt in 2 coloane, una cu descrierea informatiei 
    si una cu informatia
    extragem informatiile din fiecare coloana in cate o lista si dupa unim cele 2 coloane
    
    caracteristicile unui apartament sunt in 2 coloane
    o coloana contine caracterstica (numarul de camere)
    cealalta coloana contine valoarea (4 <camere>)
    '''

    
    try:
        coloana = anunt.find_all('div', {'class':"property_label"})
        descriere = anunt.find_all('div', {'class':'property_prop'})
        lista_coloana=[]
        lista_descriere=[]
    except AttributeError:
        print(link)
        print('probleme cu caracteristicile coloana-descriere')
        return None
    

    
    '''
    --------------UNIM CELE 2 COLOANE------------
    '''
    
    for i in coloana:
        cuvant = i.text
        cuvant = cuvant.replace(':', '')
        #excludem din string :
        cuvant = cuvant.replace('\xa0', 'Descriere suplimentara cladire')
        #aveam un loc gol in colaone care in textul html era marcat cu "\xa0"
        #si continea o descriere suplimentare a cladirii cum ar fi izolat termic
        lista_coloana.append(cuvant)

    for i in descriere:
        cuvant = i.text
        cuvant = cuvant.replace(' m2', '')
        #suprafata va contine si " m2"
        #am ales sa exclud "m2" pentru a avea doar date numerice
        lista_descriere.append(cuvant)
    
    dictionar = dict(zip(lista_coloana, lista_descriere))
    #vom face din cele 2 liste un dictionar
    #in cheie vom avea coloana unde se afla descrierea informatiei (Suprafata)
    #in valoare vom avea informatia (50 <mp>)
    
    
    
    dictionar['titlu']=titlu_anunt
    dictionar['descriere']=descriere_text
    dictionar['pret']=pret
    dictionar['link']=link
    
    
    '''
    --------------UTILITATI------------
    vom extrage ce se afla la utilitati
    la inceput fiecare apartament va avea un dictionar cu utilitati
    dupa vom uni dictionarul cu utilitati cu cel final
    '''
    
    
    dict_utilitati = {}
    try:
        cheie_utilitati =  anunt.find('fieldset', {'id':'utilitati'}).b.text
        cheie_utilitati = cheie_utilitati.replace(' ', '')
        cheie_utilitati = cheie_utilitati.replace(':', '')
        #cheia, coloana,  cu bold
        detalii_utilitati = anunt.find('fieldset', {'id':'utilitati'}).find_all('img')
        lista_utilitati = []
        for i in detalii_utilitati:
            j = i['alt']
            #valorea se afla in atributul "alt" al tag-ului img
            lista_utilitati.append(j)
        dict_utilitati[cheie_utilitati]=','.join(lista_utilitati)
    except AttributeError: 
        dict_utilitati['Utilitati']=None
        print('probleme cu utilitatile')
    
    
    
    
    '''
    --------------FINISAJE------------
    Vom extrage finisajelele si le vom pune in dictionar
    '''
    #vom extrage textul din codul html unde se afla utilitatile
    try:
        finisaje = anunt.find('fieldset', {'id':'finisari'}).get_text()
    except AttributeError:
        print(link)
        print('probleme cu finisajele')
        return None


    
    '''
    Prin functia de mai jos vom separa cu o virgula atunci cand urmatorul caracter
    este uppercase. vom dori sa returnam un string, vom pune dupa PVC o virgula si un spatiu
    si dupa vom face un split la fiecare virgula 
    pentru ca fiecare element sa fie intr-o lista "finis"
    '''
    def split_uppercase(s):
        r = []
        l = False
        for c in s:
            # l being: last character was not uppercase
            if l and c.isupper():
                r.append(',')
            l = not c.isupper()
            r.append(c)
        return ''.join(r)

    finisaje_mod = split_uppercase(finisaje)
    finisaje_mod = finisaje_mod.replace('PVC', 'PVC, ')
    #print(finisaje_mod)
    
    finis = finisaje_mod.split(',')
    
    #print('\n\n\n\n\n\n')
    #print(finis)
    #print('\n\n\n\n\n\n')
    
    
    '''
    --------DIN LISTA DE FINISAJE AM SEPARAT FIECARE CUVANT SI L-AM PUS INTR-O LISTA--------
    '''
    
    
    
    lista_key=[]

    
   # dict_finisaje = {}
    
   
    '''
    pentru ca am avut probleme cu spatiile de dupa numele variabilei, 
    (unele aveau spatiu dupa cuvant, altele nu)
    am dorit sa punem un key nou
    '''
    
    lista_key_noi = ['finisaje', 'pardosea', 'pereti', 'geamuri_usi', 'bucatarie', 'baie', 'dotari']
    lista_expresii = [r'.*Finisaje.*' , r'.*Pardoseala.*', r'.*Pereti.*', r'.*Geamuri si usi.*', r'.*Finisaj bucatarie.*', r'.*Finisaj baie.*', r'.*Dotari.*']

    for idx, i in enumerate(finis):
        if i == '\n':
            del finis[idx]
            
    for nou, expresie in zip(lista_key_noi, lista_expresii):
        for idx, i in enumerate(finis):
            match_regex = re.match( expresie, i)
            if match_regex:
                i = i.replace(i, nou)
                #print('da')
                #print(i)
                finis[idx]=i
    
    #for index, value in finis:
    dict_special={}
    
    '''
    lista descrieri va contine cheia pentru fiecare nou dictionar din finisaje
    adica va contine pereti, dotari, bucatarie etc
    
    descrierile vor fi cu litera mica, asa ca vom cauta in lista finis
    toate cuvintele care incepe cu litera mica
    '''
    
    lista_descrieri = []    
    for i in finis:
        merge = re.match(r'[a-z].*', i)
        if merge:
            lista_descrieri.append(i)    
    
    
    '''
    in lista "finis" se afla toate cuvintele din Finisaje
    cheile, coloanele sunt in lista_descrieri
    fiecare cheie are valori pana la urmatoarea cheie
    '''
    for index, value in enumerate(lista_descrieri):
        value1 = value
        index2 = lista_descrieri.index(value) + 1
        lista_finisaje = []
        try:
            value2 = lista_descrieri[index2]
            value1_index = finis.index(value1)
            value2_index = finis.index(value2)
            
            for i in finis[value1_index+1:value2_index]:
                lista_finisaje.append(i)
            value_finisaje = ','.join(lista_finisaje)
            dict_special[value1]=value_finisaje
        except IndexError:
            value1_index = finis.index(value1)
            for i in finis[value1_index+1:]:
                lista_finisaje.append(i)
            value_finisaje = ','.join(lista_finisaje)
            dict_special[value1]=value_finisaje
    
    
    dictionar_final={}
    def merge_two_dicts(x, y):
        z = x.copy()   
        z.update(y)    
        return z
    #unim dictionarul initial cu cel cu utilitati si cu cel cu finisaje
    dictionar_final = merge_two_dicts(dictionar, dict_utilitati)
    dictionar_final = merge_two_dicts(dictionar_final, dict_special)
    
    #redenumim cheile pentru a putea controla mai bine dictionarul    
    lista_veche = ['pret', 'Nr. bai', 'finisaje', 'Nr. terase', 'geamuri_usi', 'Descriere suplimentara cladire', 'Tip proprietate', 'Suprafata utila', 'pardosea', 'Tip Constructie', 'descriere', 'Nr. balcoane', 'titlu', 'ID', 'pereti', 'Confort', 'Compartimentare', 'Zona', 'dotari', 'link', 'Tranzactie', 'Nr. garaje', 'Suprafata construita', 'Nr. parcari', 'Nr. bucatarii', 'Nr. camere', 'baie', 'Etaj', 'Cartier', 'An Constructie', 'bucatarie', 'Utilitati']    
    lista_noua = ['pret', 'numar_bai', 'finisaje', 'numar_terase', 'geamuri_usi', 'descriere_suplimentara', 'tip_proprietate', 'suprafata_utila', 'pardosea', 'tip_constructie', 'descriere', 'numar_balcoane', 'titlu', 'ID', 'pereti', 'confort', 'compartimentare', 'zona', 'dotari', 'link', 'tranzactie', 'numar_garaje', 'suprafata_construita', 'numar_parcari', 'numar_bucatarii', 'numar_camere', 'baie', 'etaj', 'cartier', 'an_constructie', 'bucatarie', 'utilitati']    
    
    dictionar_scris= {}
    for v, n in zip(lista_veche, lista_noua):
        try:
            dictionar_scris[n] = copy.deepcopy(dictionar_final[v])
        except copy.error:
            dictionar_scris[n] = None
        except KeyError:
            dictionar_scris[n]= None
    
    '''   
    pentru a extrage geolocatia avem nevoie de zona completa
    aceasta va fi un string si va contine orasul, cartierul si daca avem si zona
    '''
    if dictionar_scris['zona']!=None:
        dictionar_scris['zona_completa'] = "Cluj-Napoca, " + dictionar_scris['cartier'] + ", " + dictionar_scris['zona']
    else:
        dictionar_scris['zona_completa'] = "Cluj-Napoca, " + dictionar_scris['cartier']
        #return zona_completa
    
    #dict_final = zonacompleta(dictionar_scris)

    if printare == True:
        print(dictionar_scris)    
    return dictionar_scris

'''
S-a terminat functia care extrage informatii dintr-un link
'''
  
def linkuri(pagina, printare = False):
    html = urlopen(pagina)
    anunt= bs(html.read(), 'html.parser')
    '''
    --------Extragem toate link-urile dintr-o pagina--------
    toate link-urile le punem intr-o lista
    functia primeste ca input un link care contine pagina
    functia returneaza o lista de link-uri
    '''
    try:
        tag_h2 = anunt.find_all('h2')
        lista_a = []
        for i in tag_h2:
            #print('\n\n')
            #print(i)
            link = i.find('a')
            adresa = link['href']
            lista_a.append(adresa)
    except AttributeError:
        print('nenene')
        return None
    
    lista_linkuri = []
    inceputul_adresei = 'https://www.napocaimobiliare.ro'
    
    for i in lista_a:
        link_complet = inceputul_adresei+i
        lista_linkuri.append(link_complet)
    
    if printare == True:
        print(lista_linkuri)
    
    return lista_linkuri


def nextpage(prima_pagina, printare=False):
    '''
    Aceasta functie ne da link-ul de la urmatoarea pagina
    
    '''
    html = urlopen(prima_pagina)
    pagina= bs(html.read(), 'html.parser')
    inceputul_adresei = 'https://www.napocaimobiliare.ro'
    next_page = pagina.find('li', {'class':"next"}) # butonul de next page
    ultima_pagina = pagina.find('li', {'class':"last"})
    ultima_pagina = ultima_pagina.find('a')
    ultima_pagina = ultima_pagina['href']
    ultima_pagina = inceputul_adresei + ultima_pagina
    
    if next_page is None:
        return None

    link = next_page.find('a')
    adresa = link['href']
    adresa = inceputul_adresei+adresa
    
    if adresa is None:
        return None
    else:
        if printare == True:
            print(adresa)
        return adresa
    




def extragere_pagini(page, printare=False): #introducem prima pagina
    '''
    Aceasta functie returneaza o lista cu adresa fiecarei pagini
    '''
    list_pag = []
    html = urlopen(page)
    pagina= bs(html.read(), 'html.parser')
    inceputul_adresei = 'https://www.napocaimobiliare.ro'
    # butonul de next page
    ultima_pagina = pagina.find('li', {'class':"last"})
    ultima_pagina = ultima_pagina.find('a')
    ultima_pagina = ultima_pagina['href']
    ultima_pagina = inceputul_adresei + ultima_pagina
    #page = prima_pagina
    while(page): #cu acest while preluam intr-o lista toate paginile
        #print(page)
        
        list_pag.append(page)
        if page == ultima_pagina:
            break
        page = nextpage(page)   
    if printare == True:
        print(list_pag)
    return list_pag
    
    
def extragere_anunturi(list_pagini, printare=False):
    '''
    Aceasta functie returneaza intr-o lista toate link-urile aferente anunturilor
    '''
    lista_anunturi = []
    for i in list_pagini:
        anunturi = linkuri(i)
        for x in anunturi:
            lista_anunturi.append(x)
    if printare==True:
        print(lista_anunturi)
    return lista_anunturi


################################################################
################################################################
################################################################
################################################################
################################################################
################################################################
################################################################


def scriere(obiect ,nume_fisier): 
    '''
    obiectul este fisierul pe care dorim sa-l salvam
    trebuie sa aiba extensia txt, trebuie numele sa fie sub forma blabla.txt
    '''
    with open(nume_fisier, "wb") as file:   #Pickling
        pickle.dump(obiect, file)
        
def citire(nume_fisier, printare_type=False, printare_len=False, printare=False):
    '''citim fisierele salvate'''
    with open(nume_fisier, "rb") as file:   # Unpickling
        obiect_nou = pickle.load(file)
    if printare_type==True:
        print(type(obiect_nou))
    if printare_len==True:
        print(len(obiect_nou))
    if printare==True:
        print(obiect_nou)
    return obiect_nou

lista_pagini_fin = []
lista_anunturi_fin =[]

def stergere_valori_nule(lista_dictionare, printare_len=False):
    '''
    din unele anunturi nu am putut extrage informatiile esentiale asa ca avem None
    vom sterge aceste anunturi din lista
    '''
    lista_fara_none = []
    lista_noua = copy.deepcopy(lista_dictionare)
    if printare_len==True:
        print(len(lista_noua))
    for dictionar in lista_noua:
        if dictionar != None:
            lista_fara_none.append(dictionar)
    if printare_len==True:
        print(len(lista_fara_none))
    return lista_fara_none

def extragere_tot(link, nume_fisier, printare_len=False, printare_type=False, printare=False):
    '''
    Aceasta functie extrage toate informatiile si le scrie intr-un document txt
    '''
    lista_dictionare=[]
    lista_pagini = extragere_pagini(link)
    lista_anunturi= extragere_anunturi(lista_pagini)
    for chestii in lista_anunturi:
        _ = anunt(chestii)
        lista_dictionare.append(_)
        
    lista_dictionare_none = stergere_valori_nule(lista_dictionare)    
    
    scriere(lista_dictionare_none, nume_fisier)
    if printare == True:
        print(lista_dictionare_none)
    if printare_len == True:
        print(len(lista_dictionare_none))
    if printare_type == True:
        print(type(lista_dictionare_none))
    return lista_dictionare_none

'''
Am incercat sa vad daca functioneaza pentru un anunt

#primul = anunt('https://www.napocaimobiliare.ro/va1-71492-apartament-o-camera-de-vanzare-in-buna-ziua-cluj-napoca', printare=True)
#print(primul)
'''

'''
Am extras toate anunturile cu apartamente de vanzare si de inchiriat si le-am pus in fisierele
'vanzari.txt'
'chirii.txt'
Fiecare fisier contine o lista cu mai multe dictionare. Fiecare dictionar reprezinta un anunt.
In aceasta faza inca nu au fost puse coordonale zonelor.

'''

'''
Extragerea anunturilor
'''
#lista_vanzari = extragere_tot('https://www.napocaimobiliare.ro/vanzare-apartamente-cluj', 'vanzari.txt', printare_len=True, printare_type=True)
#lista_chirii = extragere_tot('https://www.napocaimobiliare.ro/inchiriere-apartamente-cluj', 'chirii.txt', printare_len=True, printare_type=True)

'''
Citirea rezultatelor din fisierele scries
'''
lista_vanzari = citire('vanzari.txt', printare_type=True, printare_len=True, printare=False)
lista_chirii = citire('chirii.txt', printare_type=True, printare_len=True, printare=False)


def zone_dictionar(lista_dictionare):
    '''
    fiecare anunt va fi stocat intr-un dictionar si fiecare dictionar 
    intr-o lista care va contine toate anunturile
    
    extragem intr-o lista pe care o transformam intr-un set toate zonele
    '''
    lista_zone=[]
    for dictionar in lista_dictionare:
        if dictionar is None:
            break
        else:
            for key in dictionar.items():
                lista_zone.append(dictionar['zona_completa'])
    set_zone = set(lista_zone)
    return set_zone


def coordonate(element):
    '''
    aceasta functie extrage pentru o anumita zona geolocatia
    pentru ca folosim un api gratuit se returneaza o eroare 
    daca extragem prea multe anunturi
    
    '''
    try:
        time.sleep(2)
        zona = Geocoder.geocode(element)
        #dictionar_zone[element]=zona.coordinates
        
        rezultat = zona.coordinates
        for i in range(20):
            if rezultat == None:
                time.sleep(5)
                zona = Geocoder.geocode(element)
                rezultat = zona.coordinates
            else:
                print('a mers ' + str(element) + " " + str(rezultat))
                return rezultat
                break

    except requests.ConnectionError as e: #am primit eroare de conectare asa ca am pus sa incerce inca o data dupa 120 de secunde
        time.sleep(120)
        print(element)
        coordonate(element)
    except GeocoderError:
        time.sleep(10)
        coordonate(element)
        
def coordonate_toate(lista_zone, fisier_txt):
    contor = len(lista_zone)
    dictionar_zone = {}
    for i in lista_zone:
        dictionar_zone[i] = coordonate(i)
        print(i)
        contor = contor - 1
        print("au mai ramas " + str(contor) + " zone")
    scriere(dictionar_zone, fisier_txt)
    return dictionar_zone

def adaugare_coordonate(lista_cu_dictionare, fisier_lista_coordonate):
    #_ = coordonate_cartiere(lista_cu_dictionare, fisier_zone_cartiere)
    
    dict_zone = citire(fisier_lista_coordonate)
    
    for dictionar in lista_cu_dictionare:
        try:
            zona = dictionar['zona_completa']
            zona_fin = dict_zone[zona]
            dictionar['lat']=zona_fin[0]
            dictionar['long']=zona_fin[1]
        except KeyError:
            dictionar['lat']=None
            dictionar['long']=None
        except TypeError as t:
            
            continue
            #dictionar['lat']=None
            #dictionar['long']=None
    return lista_cu_dictionare


def lat_long(lista_dictionare, fisier_scris_zone, document_zone, fisier_complet):
    '''
    pentru ca procesul de extragere a coordonatelor este unul incet
    am ales sa citesc din fisiere in care am mai salvat coordonate pentru zone
    coodonatele pentru a nu lua atata timp
    '''
    set_zone = zone_dictionar(lista_dictionare)
    lista_zone = list(set_zone)
    dictionar_document = citire(document_zone)
    dictionar_zone = {}
    #aici upgradez dictionarul cu zonele pe care nu le-am avut in fisierul salvat
    for i in lista_zone:
        if i in dictionar_document:
            if dictionar_document[i] != None:
                dictionar_zone[i] = dictionar_document[i]
            else:
                dictionar_zone[i] = coordonate(i)
                print(i)
        else:
            dictionar_zone[i] = coordonate(i)
            print(i)
    scriere(dictionar_zone, fisier_scris_zone)
    lista_finala = copy.deepcopy(lista_dictionare)
    
    for dictionar in lista_finala:
        try:
            zona = dictionar['zona_completa']
            zona_fin = dictionar_zone[zona]
            dictionar['lat']=zona_fin[0]
            dictionar['long']=zona_fin[1]
        except KeyError:
            dictionar['lat']=None
            dictionar['long']=None
        except TypeError as t:
            dictionar['lat']=None
            dictionar['long']=None
    scriere(lista_finala, fisier_complet)
    return lista_finala


#am extras coordonatele cu lat si long pentru vanzari


'''
am comentat linia de cod de mai jos ca sa nu extraga iar coordonatele zonelor care au fost extrase
'''
#lista_lat_long = lat_long(lista_chirii, 'zone_noi_3.txt', 'zone_noi_2.txt', 'lista_chirii2.txt')
#print(lista_lat_long)
#print(len(lista_lat_long))        




def functie_csv(fisier_de_citit, fisier_csv):
    '''
    aceasta functie scrie intr-un fisier csv toate anunturile
    '''
    lista_dictionare = citire(fisier_de_citit)
    with open(fisier_csv, 'w', encoding='utf-8') as f:
        coloane = ['pret', 'numar_bai', 'finisaje', 'numar_terase', 'geamuri_usi', 'descriere_suplimentara', 'tip_proprietate', 'suprafata_utila', 'pardosea', 'tip_constructie', 'descriere', 'numar_balcoane', 'titlu', 'ID', 'pereti', 'confort', 'compartimentare', 'zona', 'dotari', 'link', 'tranzactie', 'numar_garaje', 'suprafata_construita', 'numar_parcari', 'numar_bucatarii', 'numar_camere', 'baie', 'etaj', 'cartier', 'an_constructie', 'bucatarie', 'utilitati', 'lat', 'long', 'zona_completa']
        csv_writer= csv.DictWriter(f, fieldnames=coloane, quoting=csv.QUOTE_ALL, dialect='excel')
        csv_writer.writeheader()
        for dictionar in lista_dictionare:
            if dictionar is None:
                csv_writer.writerow({'titlu': 'Nu a fost deschis anuntul'})
            else:
                try:
                    csv_writer.writerow({'pret':dictionar['pret'], 'numar_bai':dictionar['numar_bai'], 'finisaje':dictionar['finisaje'], 'numar_terase':dictionar['numar_terase'], 'geamuri_usi':dictionar['geamuri_usi'], 'descriere_suplimentara':dictionar['descriere_suplimentara'], 'tip_proprietate':dictionar['tip_proprietate'], 'suprafata_utila':dictionar['suprafata_utila'], 'pardosea':dictionar['pardosea'], 'tip_constructie':dictionar['tip_constructie'], 'descriere':dictionar['descriere'], 'numar_balcoane':dictionar['numar_balcoane'], 'titlu':dictionar['titlu'], 'ID':dictionar['ID'], 'pereti':dictionar['pereti'], 'confort':dictionar['confort'], 'compartimentare':dictionar['compartimentare'], 'zona':dictionar['zona'], 'dotari':dictionar['dotari'], 'link':dictionar['link'], 'tranzactie':dictionar['tranzactie'], 'numar_garaje':dictionar['numar_garaje'], 'suprafata_construita':dictionar['suprafata_construita'], 'numar_parcari':dictionar['numar_parcari'], 'numar_bucatarii':dictionar['numar_bucatarii'], 'numar_camere':dictionar['numar_camere'], 'baie':dictionar['baie'], 'etaj':dictionar['etaj'], 'cartier':dictionar['cartier'], 'an_constructie':dictionar['an_constructie'], 'bucatarie':dictionar['bucatarie'], 'utilitati':dictionar['utilitati'], 'lat':dictionar['lat'], 'long':dictionar['long'], 'zona_completa':dictionar['zona_completa']})
                except KeyError as e:
                    print("KeyError: {0}".format(e))
    print('Gata')
    
    


#scriere(vanzari, 'lista_vanzari2.txt')
    
    
    
'''
Scriem in fisierul csv informatiile obtinute
'''
#functie_csv('lista_vanzari2.txt', 'napoca_vanzari_iunie_11.csv' )
#functie_csv('lista_chirii2.txt', 'napoca_inchirieri_iunie_11.csv' )



