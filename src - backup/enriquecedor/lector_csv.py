import os
import pandas as pd

def generacion_softerra():
    carpeta = "input"
    ruta_softerra = os.path.join(carpeta,"softerra.xlsx")

    df_PCR= pd.read_csv("input/PCR.csv",skiprows=[1])
    df_PCR= df_PCR[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]



    df_SEC= pd.read_csv("input/SEC.csv",skiprows=[1])
    df_SEC= df_SEC[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]


    df_SBI= pd.read_csv("input/SBI.csv",skiprows=[1])
    df_SBI= df_SBI[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]

    df_SNC= pd.read_csv("input/SNC.csv",skiprows=[1])
    df_SNC= df_SNC[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]


    df_UNC= pd.read_csv("input/UNC.csv",skiprows=[1])
    df_UNC= df_UNC[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]
    df_CO2= pd.read_csv("input/CO2.csv",skiprows=[1])

    df_CO2= df_CO2[['name','company', 'countryCode', 'description','displayName', 'employeeNumber','mail','title']]


    df_final = pd.concat([df_PCR,df_SBI,df_SEC,df_SNC,df_UNC,df_CO2])
    df_final= df_final.rename(columns={"company":"company_softerra"})

    df_final.to_excel(ruta_softerra,index=False)