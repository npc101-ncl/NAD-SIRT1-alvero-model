#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb  3 11:26:06 2020

@author: peter
"""

import site, os, re
import pandas as pd
from python.pycotoolsHelpers import *
import pickle
import time

working_directory = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(working_directory,"oldModel","NAD_model_files",
                        "AMPK-NAD-PGC1a-SIRT1-model",
                        "Parameter_Estimation_Data")
run_dir = os.path.join(working_directory,'copasiRuns', 'reparam')
if not os.path.isdir(run_dir):
    os.makedirs(run_dir)

data_names = ["PE_0.5mM_AICAR_AMPK-P.txt",
              "PE_0.5mM_AICAR_NAD_and_PGC1aDeacet.txt",
              "PE_5mM_GlucRestric_NAD.txt",
              "PE_PARP_Inhib_PJ34_NAD.txt"]

indep_cond = [{"AICAR":1, "Glucose_source":0}, 
              {"AICAR":1, "Glucose_source":0}, 
              {"Glucose_source":5},
              {"PARP1":0, "AMPK_driven_NAD_source":0,
               "AMPK_driven_NegReg_source":0}]

"""    
# makes no obvious difrence
indep_cond = [{"AICAR":1, "Glucose_source":0, "Glucose":0, "GlucoseDelay":0}, 
              {"AICAR":1, "Glucose_source":0, "Glucose":0, "GlucoseDelay":0}, 
              {"Glucose_source":5},
              {"PARP1":0, "AMPK_driven_NAD_source":0,
               "AMPK_driven_NegReg_source":0}]
"""

duration = [24,12,36,24]

Fakouri_file = os.path.join(working_directory,"oldModel","NAD_model_files",
                       "AMPK-NAD-PGC1a-SIRT1-manuscript",
                       "Raw_Literature_Data",
                       "SupplFig_21_Fakouri_et_al_2017.xlsx")

NR_file = os.path.join(working_directory,"oldModel","NAD_model_files",
                       "AMPK-NAD-PGC1a-SIRT1-manuscript",
                       "Raw_Literature_Data",
                       "SupplFig_5_Canto_et_al_2012.xlsx")

myKVars = ["AMPK_phosphorylation_k1", "AMPK_dephosphorylation_k1",
           "PGC1a_phosphorylation_k1", "PGC1a_dephosphorylation_k1",
           "Induced_PGC1a_deacetylation_k1", "PGC1a_acetylation_k1",
           "DUMMY_REACTION_Delay_in_NAD_Increase_k1",
           "DUMMY_REACTION_Delay_in_NAD_Increase_2_k1", 
           "NAD_synthesis_v", "NAD_utilisation_k1",
           "NAD_utilisation_by_PARP_k1", "NAD_increase_by_AMPK_Shalve", 
           "NAD_increase_by_AMPK_V", "NAD_increase_by_AMPK_h", 
           "Deacetylation_activity_Shalve", "Deacetylation_activity_V",
           "Deacetylation_activity_h",
           "DUMMY_REACTION_AICAR_stimulus_removal_k1",
           "AMPK_phosphorylation_induced_by_AICAR_k1",
           "DUMMY_REACTION_Delay_AICAR_stimulus_Shalve",
           "DUMMY_REACTION_Delay_AICAR_stimulus_V",
           "DUMMY_REACTION_Delay_AICAR_stimulus_h", 
           "Basal_PGC1a_deacetylation_v",
           "DUMMY_REACTION_PGC1a_Deacetylation_Limiter_k1",
           "Glucose_induced_AMPK_dephosphorylation_k1", 
           "Glucose_utilisation_k1", 
           "Glucose_DUMMY_REACTION_delay_Shalve",
           "Glucose_DUMMY_REACTION_delay_V",
           "Glucose_DUMMY_REACTION_delay_h",
           "Glucose_DUMMY_REACTION_delay_limiter_k1",
           "NAD_negative_regulation_k1",
           "DUMMY_REACTION_NegReg_disappearance_k1", 
           "NR_NMN_supplementation_Shalve", "NR_NMN_supplementation_V",
           "NR_NMN_supplementation_h"]

hardCodeSuspects = ["AMPK_dephosphorylation_k1",
                    "AMPK_phosphorylation_k1", 
                    "DUMMY_REACTION_Delay_in_NAD_Increase_2_k1",
                    "DUMMY_REACTION_Delay_in_NAD_Increase_k1",
                    "Deacetylation_activity_Shalve",
                    "Deacetylation_activity_h",
                    "Glucose_induced_AMPK_dephosphorylation_k1",
                    "Glucose_utilisation_k1",
                    "NAD_increase_by_AMPK_h",
                    "NR_NMN_supplementation_Shalve",
                    "PGC1a_acetylation_k1",
                    "PGC1a_dephosphorylation_k1",
                    "PGC1a_phosphorylation_k1"]

NR_data = pd.read_excel (NR_file,sheet_name='Hoja1',skiprows=1,
                         index_col=0,usecols=3,nrows=6)
#need to check units / interpritation of this file
NR_data["NR-NMN"] = NR_data.index # /1000 my inclination would be to convert
# to mols as thats defined as the unit but alvaro said he didn't do this in
# his suplimental materials so for now I wont either.
NR_data["NAD_fold_increase"] = NR_data["Fold change"]

Fakouri_data = [pd.read_excel(Fakouri_file,sheet_name='Hoja1',skiprows=4*n,
                              usecols=[1,2],nrows=2) for n in range(6)]
Fakouri_data = {list(i.columns)[0]:i["Fold change"].iloc[1] for
                i in Fakouri_data}

mySuperComputer=False
if not mySuperComputer:
    addCopasiPath("/Applications/copasi")
    
antFile = open(os.path.join(working_directory,"modAntFile.txt"), "r")
antimony_string = antFile.read()
antFile.close()

if __name__ == "__main__":
    calPaths = []
    for fName in data_names:
        dataFile = open(os.path.join(data_dir, fName), "r")
        df = pd.read_csv(dataFile,sep='\t')
        dataFile.close()
        pathRef = os.path.join(run_dir,re.sub("(^.*)\\.txt$","\\1.csv",
                                              fName))
        renameDict = dict(zip(list(df.columns),
                              [s.strip() for s in list(df.columns)]))
        df = df.rename(columns = renameDict)
        df.to_csv(path_or_buf = pathRef)
        calPaths.append(pathRef)
    for index, row in NR_data.iterrows():
        df = pd.DataFrame([{"Time":0, "NAD_fold_increase":1},
                           {"Time":24,
                            "NAD_fold_increase":row["NAD_fold_increase"]}])
        pathRef = os.path.join(run_dir, "NR_effects"+str(index)+".csv")
        df.to_csv(path_or_buf = pathRef)
        indep_cond.append({"NR-NMN":row["NR-NMN"]})
        duration.append(24)
        calPaths.append(pathRef)
    
    myModel = modelRunner(antimony_string, run_dir)
    
    # replicating figure s21
    
    tempParams = myModel.extractModelParam()
    Fakouri_data["AMPK total"] = (tempParams["AMPK-P"]+
                 tempParams["AMPK"])*Fakouri_data["AMPK total"]
    Fakouri_data["AMPK ratio"] = (Fakouri_data["AMPK-P"]*
                tempParams["AMPK-P"]/(tempParams["AMPK"]+
                          tempParams["AMPK-P"]))
    Fakouri_data["AMPK_P"] = (Fakouri_data["AMPK ratio"]*
                Fakouri_data["AMPK total"])
    Fakouri_data["AMPK"] = (Fakouri_data["AMPK total"] - 
                Fakouri_data["AMPK-P"])
    Fakouri_data["SIRT1"] = tempParams["SIRT1"]*Fakouri_data["SIRT1"]
    Fakouri_data["PGC1a_deacet"] = (tempParams["PGC1a_deacet"]*
                Fakouri_data["PGC1a"])
    Fakouri_data["PGC1a_P"] = (tempParams["PGC1a-P"]*
                Fakouri_data["PGC1a"])
    Fakouri_data["PGC1a"] = (tempParams["PGC1a"]*
                Fakouri_data["PGC1a"])
    Fakouri_data["PARP"] = (tempParams["PARP1"]*
                Fakouri_data["PARP1"])
    Fakouri_data["NAD"] = (tempParams["NAD"]*
                Fakouri_data["NAD"])
    Fakouri_data.pop("AMPK total", None) 
    Fakouri_data.pop("AMPK ratio", None)
    Fakouri_data.pop("PARP1", None)
    Fakouri_data.pop("AMPK-P", None)
    
    Fakouri_sim = myModel.runSteadyStateFinder(params=Fakouri_data)
    
    file = open(os.path.join(working_directory,'old-Fakouri.p'),'wb')
    pickle.dump({"modParams":tempParams,
                 "data":Fakouri_data,
                 "sim":Fakouri_sim}, file)
    file.close()
    
    # replication of the independent conditions associated experamental
    # inputs for comparision.
    
    df = pd.DataFrame(indep_cond)
    
    df = myModel.preProcessParamEnsam(df)
    
    timeCourse = myModel.runTimeCourse(duration, adjustParams=df,
                                       stepSize=0.25)
    file = open(os.path.join(working_directory,'old-timeCourses.p'),'wb')
    pickle.dump(timeCourse, file)
    file.close()
    myModel.clearRunDirectory()
    
    # a run of the unperturbed model
    
    timeCourse = myModel.runTimeCourse(24,stepSize=0.25) 
    
    file = open(os.path.join(working_directory,'old-timeCoursesN.p'),'wb')
    pickle.dump(timeCourse, file)
    file.close()
    myModel.clearRunDirectory()
    
    # replicating figure s27 branched time serise
    # 0.5mM AICAR treatment with optional pretreatment (24h prior) with
    # 0.5mM Nicotinamide Riboside or 1µM PJ34
    
    timeCourseGI = myModel.runTimeCourse(24,stepSize=0.25,
                                         adjustParams=pd.DataFrame([{
                                                 "PARP1":2.5}]))
    
    file = open(os.path.join(working_directory,'old-timeCoursesGI.p'),'wb')
    pickle.dump(timeCourseGI, file)
    file.close()
    
    timeCourseGINR = myModel.runTimeCourse(24,stepSize=0.25,
                                           adjustParams=pd.DataFrame([{
                                                   "PARP1":2.5,
                                                   "NR-NMN":500}]))
    
    timeCourseGIPJ = myModel.runTimeCourse(24,stepSize=0.25,
                                           adjustParams=pd.DataFrame([{
                                                   "PARP1":0}]))
    
    df = myModel.TCendState(timeCourseGINR, variables = "metabolites")
    df["PARP1"] = 2.5
    df["NR-NMN"] = 0
    df["AICAR"] = 1
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourseGINR = myModel.runTimeCourse(12,stepSize=0.25,
                                           adjustParams=df)
    
    df = myModel.TCendState(timeCourseGI, variables = "metabolites")
    df["AICAR"] = 1
    df["PARP1"] = 2.5
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourseGIA = myModel.runTimeCourse(12,stepSize=0.25,
                                          adjustParams=df)
    
    df = myModel.TCendState(timeCourseGIPJ, variables = "metabolites")
    df["AICAR"] = 1
    df["PARP1"] = 2.5
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourseGIPJ = myModel.runTimeCourse(12,stepSize=0.25,
                                           adjustParams=df)
    
    df = myModel.TCendState(timeCourse, variables = "metabolites")
    df["AICAR"] = 1
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourseA = myModel.runTimeCourse(12,stepSize=0.25, adjustParams=df)
    
    df = myModel.TCendState(timeCourse, variables = "metabolites")
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourse = myModel.runTimeCourse(12,stepSize=0.25, adjustParams=df)
    
    df = myModel.TCendState(timeCourseGI, variables = "metabolites")
    df["PARP1"] = 2.5
    df = df.drop(columns=["SIRT1_activity"])
    print(df.squeeze())
    
    timeCourseGI = myModel.runTimeCourse(12,stepSize=0.25, adjustParams=df)
    
    s27fig = {"ctrl-wt":myModel.TCendState(timeCourse,
                                           variables = "metabolites"),
              "ctrl-gi":myModel.TCendState(timeCourseGI,
                                           variables = "metabolites"),
              "aic-wt":myModel.TCendState(timeCourseA,
                                          variables = "metabolites"),
              "aic-gi":myModel.TCendState(timeCourseGIA,
                                          variables = "metabolites"),
              "nr+aic-gi":myModel.TCendState(timeCourseGINR,
                                             variables = "metabolites"),
              "pj34+aic-gi":myModel.TCendState(timeCourseGIPJ,
                                               variables = "metabolites")}
              
    file = open(os.path.join(working_directory,'old-S27fig.p'),'wb')
    pickle.dump(s27fig, file)
    file.close()