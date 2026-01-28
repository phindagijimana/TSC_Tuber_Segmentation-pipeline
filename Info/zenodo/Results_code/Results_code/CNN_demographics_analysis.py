# -*- coding: utf-8 -*-
"""
Created on Thu Aug  8 18:22:42 2024

@author: Ivan Sanchez Fernandez
"""

# Upload needed packages
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from scipy.stats import chi2_contingency
from scipy.stats import kruskal
from scipy.stats import false_discovery_control




# Import the data of CNN cases
CNN_cases = pd.read_excel('//rc-fs/neuro-peters/Public/CNN/DEMOGRAPHICS/01 Original demographic data/For Ivan_CNN Training data set.xlsx')

# Columns in the dataframe
CNN_cases.columns

# Select only the needed columns
CNN_cases = CNN_cases[['PatientID', 'Original ID', 'Original data set', 'Segmentation']]

# Drop duplicates
CNN_cases = CNN_cases.drop_duplicates('PatientID')

# Reclassify case219 as manual segmentation because there were 2 rows, 1 with automatic and 1 with manual segmentation (see the original For Ivan_CNN Training data set.xlsx file)
CNN_cases.loc[CNN_cases['PatientID']=='Case219', 'Segmentation'] = 'Manual'

# Rename case177 (PatientID 163) to case095 (PatientID 149) because they were found to be the same patient (see README file, Boston Children's Hospital demographics) 
CNN_cases.loc[CNN_cases['Original ID']=='case177', 'Original ID'] = 'case095'




# Import the TACERN data
TACERN_data = pd.read_csv('//rc-fs/neuro-peters/Public/CNN/DEMOGRAPHICS/01 Original demographic data/20200813-tacern-dtitracts-data2.csv', parse_dates=['DOS', 'DOB'])

# Columns in the dataframe
TACERN_data.columns

# Select only the needed columns
TACERN_data = TACERN_data[['site_id', 'screening_id', 'scanID', 'DOB', 'DOS','age_scan', 'sex']]

# Drop duplicates
TACERN_data = TACERN_data.drop_duplicates(subset=['screening_id', 'scanID'])

# Calculate age at MRI
TACERN_data['age_at_MRI'] = np.round(((TACERN_data['DOS'] - TACERN_data['DOB']).apply(lambda s: s.days) / 365.2422), decimals=2)

# Eliminate duplicate rows
TACERN_data = TACERN_data.drop_duplicates()

# Recodify sex
TACERN_data['male_sex_at_birth'] = np.where(TACERN_data['sex']=='M', 'yes', 'no')

# Select only the needed columns
TACERN_data = TACERN_data[['screening_id', 'scanID', 'age_at_MRI', 'male_sex_at_birth', 'DOB']]

# Rename columns
TACERN_data = TACERN_data.rename(columns = {'scanID': 'MRI_number_TACERN', 'age_at_MRI': 'age_at_MRI_TACERN', 'male_sex_at_birth': 'male_sex_at_birth_TACERN', 'DOB': 'date_of_birth_TACERN'})

# Left-join the dataframes
CNN_cases = pd.merge(CNN_cases, TACERN_data, 
                     left_on='Original ID', 
                     right_on='screening_id',
                     how='left')




# Some TACERN cases did not have information on the 20200813-tacern-dtitracts-data2.csv file, so we found some more information on the ACE_RDCRN_Overlap_2022_07_06.xlsx file, ACE sheet

# Missing data
CNN_cases[CNN_cases['Original data set']=='TACERN'][CNN_cases['age_at_MRI_TACERN'].isnull() | CNN_cases['male_sex_at_birth_TACERN'].isnull()]

# Import the TACERN additional data (only the 121 first rows because the other rows are in a different format)
TACERN_additional_data = pd.read_excel('//rc-fs/neuro-peters/Public/CNN/DEMOGRAPHICS/01 Original demographic data/data_overlap/ACE_RDCRN_Overlap_2022_07_06.xlsx', 'ACE', parse_dates=['DOS', 'DOB'])

# Columns in the dataframe
TACERN_additional_data.columns

# Calculate age at MRI
TACERN_additional_data['age_at_MRI'] = np.round(((TACERN_additional_data['DOS'] - TACERN_additional_data['DOB']).apply(lambda s: s.days) / 365.2422), decimals=2)

# Recodify sex
TACERN_additional_data['male_sex_at_birth'] = np.where(TACERN_additional_data['gender']=='M', 'yes', 'no')

# Select only the needed columns
TACERN_additional_data = TACERN_additional_data[['screening_id', 'scanID', 'age_at_MRI', 'male_sex_at_birth', 'DOB']]

# Keep only the rows with information that is missing in the CNN_cases
missing_patients = CNN_cases[CNN_cases['Original data set']=='TACERN'][CNN_cases['age_at_MRI_TACERN'].isnull() | CNN_cases['male_sex_at_birth_TACERN'].isnull()]['Original ID']

TACERN_additional_data = TACERN_additional_data[TACERN_additional_data['screening_id'].isin(missing_patients)]

# Rename columns
TACERN_additional_data = TACERN_additional_data.rename(columns = {'screening_id': 'Original ID', 'scanID': 'MRI_number_TACERN_additional_data', 'age_at_MRI': 'age_at_MRI_TACERN_additional_data', 'male_sex_at_birth': 'male_sex_at_birth_TACERN_additional_data', 'DOB': 'date_of_birth_TACERN_additional_data'})

# Make same data type than CNN_cases
TACERN_additional_data['MRI_number_TACERN_additional_data'] = np.float64(TACERN_additional_data['MRI_number_TACERN_additional_data'])

# Add the additional TACERN data to the missing data
CNN_cases = pd.merge(CNN_cases, TACERN_additional_data, how='left', on='Original ID')




# Import the Boston Children's Hospital data
BCH_data = pd.read_csv('//rc-fs/neuro-peters/Public/CNN/DEMOGRAPHICS/01 Original demographic data/BCH_data.csv', parse_dates=['date_of_birth', 'date_of_MRI'])

# Columns in the dataframe
BCH_data.columns

# Calculate age at MRI
BCH_data['age_at_MRI'] = np.round(((BCH_data['date_of_MRI'] - BCH_data['date_of_birth']).apply(lambda s: s.days) / 365.2422), decimals=2)

# Select only the needed columns
BCH_data = BCH_data[['ID', 'MRI_number', 'age_at_MRI', 'male_sex_at_birth', 'date_of_birth']]

# Rename columns
BCH_data = BCH_data.rename(columns = {'MRI_number': 'MRI_number_BCH', 'age_at_MRI': 'age_at_MRI_BCH', 'male_sex_at_birth': 'male_sex_at_birth_BCH', 'date_of_birth': 'date_of_birth_BCH'})

# Left-join the dataframes
CNN_cases = pd.merge(CNN_cases, BCH_data, 
                     left_on='Original ID', 
                     right_on='ID',
                     how='left')




# Import the RDCRN data
RDCRN_data = pd.read_excel('//rc-fs/neuro-peters/Public/CNN/DEMOGRAPHICS/01 Original demographic data/RDCRN_dataquality.xlsx')

# Columns in the dataframe
RDCRN_data.columns

# Convert dates to date variable
RDCRN_data['DOB'] = pd.to_datetime(RDCRN_data['DOB'], format='mixed')
RDCRN_data['DOS'] = pd.to_datetime(RDCRN_data['DOS'], format='mixed')

# Calculate age at MRI
RDCRN_data['age_at_MRI'] = np.round(((RDCRN_data['DOS'] - RDCRN_data['DOB']).apply(lambda s: s.days) / 365.2422), decimals=2)

# Eliminate blank space from the sex column
RDCRN_data['sex'] = RDCRN_data['sex'].str.strip()

# Recodify sex
RDCRN_data['male_sex_at_birth'] = np.where(RDCRN_data['sex']=='M', 'yes', 'no')

# Select only the needed columns
RDCRN_data = RDCRN_data[['caseID', 'scanID', 'age_at_MRI', 'male_sex_at_birth', 'DOB']]

# Rename columns
RDCRN_data = RDCRN_data.rename(columns = {'scanID': 'MRI_number_RDCRN', 'age_at_MRI': 'age_at_MRI_RDCRN', 'male_sex_at_birth': 'male_sex_at_birth_RDCRN', 'DOB': 'date_of_birth_RDCRN'})

# Left-join the dataframes
CNN_cases = pd.merge(CNN_cases, RDCRN_data, 
                     left_on='Original ID', 
                     right_on='caseID',
                     how='left')




# Reorganize the variables into consistent columns
CNN_cases['MRI_number'] = np.select(
    [
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['MRI_number_TACERN'])==False),
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['MRI_number_TACERN_additional_data'])==False),
     CNN_cases['Original data set']=="BCH"
     ],
    [
     CNN_cases['MRI_number_TACERN'],
     CNN_cases['MRI_number_TACERN_additional_data'],     
     CNN_cases['MRI_number_BCH']
     ],
    default = CNN_cases['MRI_number_RDCRN']
    )


CNN_cases['age_at_MRI'] = np.select(
    [
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['age_at_MRI_TACERN'])==False),
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['age_at_MRI_TACERN_additional_data'])==False),
     CNN_cases['Original data set']=="BCH"
     ],
    [
     CNN_cases['age_at_MRI_TACERN'],
     CNN_cases['age_at_MRI_TACERN_additional_data'],
     CNN_cases['age_at_MRI_BCH']
     ],
    default = CNN_cases['age_at_MRI_RDCRN']
    )


CNN_cases['male_sex_at_birth'] = np.select(
    [
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['male_sex_at_birth_TACERN'])==False),
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['male_sex_at_birth_TACERN_additional_data'])==False),
     CNN_cases['Original data set']=="BCH"
     ],
    [
     CNN_cases['male_sex_at_birth_TACERN'],
     CNN_cases['male_sex_at_birth_TACERN_additional_data'],
     CNN_cases['male_sex_at_birth_BCH']
     ],
    default = CNN_cases['male_sex_at_birth_RDCRN']
    )


CNN_cases['date_of_birth'] = np.select(
    [
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['date_of_birth_TACERN'])==False),
     (CNN_cases['Original data set']=="TACERN") & (pd.isna(CNN_cases['date_of_birth_TACERN_additional_data'])==False),
     CNN_cases['Original data set']=="BCH"
     ],
    [
     CNN_cases['date_of_birth_TACERN'],
     CNN_cases['date_of_birth_TACERN_additional_data'],
     CNN_cases['date_of_birth_BCH']
     ],
    default = CNN_cases['date_of_birth_RDCRN']
    )




# Select only the needed columns
CNN_cases = CNN_cases[['PatientID', 'MRI_number', 'Segmentation', 'age_at_MRI', 'male_sex_at_birth', 'date_of_birth', 'Original data set']]




# Extract the names of the cases and MRI numbers with MRIs
path = Path('//rc-fs/neuro-peters/Public/CNN/IMAGING/01MRIs')
files = [file.name for file in path.rglob('*')]

# Save the case and scan in lists
case_list = []
for MRI in files:
    case_list.append(['Case' + MRI.split('case')[1].split('_')[0], float(MRI.split('_s')[1].split('_')[0])])


# Create pandas dataframe with case and scan
CNN_MRIs = pd.DataFrame(case_list, columns=['PatientID', 'MRI_number'])

# Eliminate duplicate rows
CNN_MRIs = CNN_MRIs.drop_duplicates()




# Select only the patients who had MRI
CNN_data = pd.merge(CNN_MRIs, CNN_cases, 
                     on=['PatientID', 'MRI_number'],
                     how='left')

# Eliminate duplicate rows
CNN_data = CNN_data.drop_duplicates()


# Check for missing data
CNN_data[CNN_data.isnull().any(axis=1)]




# Check for potential overlapped patients between BCH, TACERN, and RDCRN
potential_overlap = CNN_data[CNN_data.duplicated('date_of_birth', keep=False)]

check_potential_overlap_patients = potential_overlap.loc[potential_overlap.groupby('date_of_birth')['PatientID'].transform('nunique').gt(1)].sort_values('date_of_birth')




# Extract the names of the cases and MRI numbers with MRIs after having eliminated the duplicated cases
path = Path('//rc-fs/neuro-peters/Public/CNN/IMAGING/02.1MRIsnoduplicated')
files = [file.name for file in path.rglob('*')]

# Save the case and scan in lists
case_list = []
for MRI in files:
    case_list.append(['Case' + MRI.split('case')[1].split('_')[0], float(MRI.split('_s')[1].split('_')[0])])


# Create pandas dataframe with case and scan
CNN_MRIs_no_duplicated = pd.DataFrame(case_list, columns=['PatientID', 'MRI_number'])

# Eliminate duplicate rows
CNN_MRIs_no_duplicated = CNN_MRIs_no_duplicated.drop_duplicates()


# Select only the patients who had no duplicated MRI
CNN_data_no_duplicated = pd.merge(CNN_MRIs_no_duplicated, CNN_cases, 
                     on=['PatientID', 'MRI_number'],
                     how='left')

# Eliminate duplicate rows
CNN_data_no_duplicated = CNN_data_no_duplicated.drop_duplicates()


# Check for missing data
CNN_data_no_duplicated[CNN_data_no_duplicated.isnull().any(axis=1)]


# Eliminate the cases which were found to be low quality on resegmenting (case 213 only has to eliminate MRI 02)
low_quality_MRI = ['Case002', 'Case024', 'Case027', 'Case043', 'Case059', 'Case064', 'Case083', 'Case116', 'Case117', 'Case135', 'Case139', 'Case141', 'Case148']

CNN_data_no_duplicated = CNN_data_no_duplicated.drop(CNN_data_no_duplicated[CNN_data_no_duplicated['PatientID'].isin(low_quality_MRI)].index)

CNN_data_no_duplicated = CNN_data_no_duplicated.drop(CNN_data_no_duplicated[CNN_data_no_duplicated['PatientID'] == 'Case213'][CNN_data_no_duplicated['MRI_number'] == 2.0].index)








## DEMOGRAPHICS

# Number of patients
number_of_patients = len(pd.unique(CNN_data_no_duplicated['PatientID']))
print(f"The number of patients is: {number_of_patients}.")


# Number of MRIs
number_of_MRIs = len(CNN_data_no_duplicated['PatientID'])
print(f"The number of MRIs is: {number_of_MRIs}.")


# Number of MRIs per patient
number_of_MRIs_per_patient = CNN_data_no_duplicated.groupby('PatientID').size().value_counts()
number_of_MRIs_per_patient_proportion = np.round(CNN_data_no_duplicated.groupby('PatientID').size().value_counts(normalize=True), decimals=3)
print(f"The number of MRIs per patient is: {number_of_MRIs_per_patient[1]} ({number_of_MRIs_per_patient_proportion[1]}) patients had 1 MRI, {number_of_MRIs_per_patient[2]} ({number_of_MRIs_per_patient_proportion[2]}) patients had 2 MRIs, and {number_of_MRIs_per_patient[3]} ({number_of_MRIs_per_patient_proportion[3]}) patients had 3 MRIs.")


# Calculate age statistics
age_median = np.round(CNN_data_no_duplicated['age_at_MRI'].median(), decimals=1)
age_quantile = np.round(CNN_data_no_duplicated['age_at_MRI'].quantile([0.25, 0.75]), decimals=1)
age_mean = np.round(CNN_data_no_duplicated['age_at_MRI'].mean(), decimals=1)
age_standard_deviation = np.round(CNN_data_no_duplicated['age_at_MRI'].std(), decimals=1)
print(f"The median (p25-p75) age at MRI is: {age_median} ({list(age_quantile)[0]}-{list(age_quantile)[1]}) years.")
print(f"The mean (standard deviation) age at MRI is: {age_mean} ({age_standard_deviation}) years.")


# Calculate sex statistics
sex_frequencies = CNN_data_no_duplicated.drop_duplicates('PatientID')['male_sex_at_birth'].value_counts()
sex_proportions = np.round(CNN_data_no_duplicated.drop_duplicates('PatientID')['male_sex_at_birth'].value_counts(normalize=True), decimals=3)
print(f"The sex distribution of the patients is: {list(sex_frequencies)[0]} ({list(sex_proportions)[0]}) males and {list(sex_frequencies)[1]} ({list(sex_proportions)[1]}) females.")


# Calculate origin of the dataset statistics
data_origin_frequencies = CNN_data_no_duplicated.drop_duplicates('PatientID')['Original data set'].value_counts()
data_origin_proportions = np.round(CNN_data_no_duplicated.drop_duplicates('PatientID')['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies)[0]} ({list(data_origin_proportions)[0]}) patients from TACERN, {list(data_origin_frequencies)[1]} ({list(data_origin_proportions)[1]}) patients from RDCRN, and {list(data_origin_frequencies)[2]} ({list(data_origin_proportions)[2]}) patients from BCH.")


# Calculate origin of the dataset MRI statistics
data_origin_frequencies_MRI = CNN_data_no_duplicated['Original data set'].value_counts()
data_origin_proportions_MRI = np.round(CNN_data_no_duplicated['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_MRI)[0]} ({list(data_origin_proportions_MRI)[0]}) MRIs from TACERN, {list(data_origin_frequencies_MRI)[1]} ({list(data_origin_proportions_MRI)[1]}) MRIs from RDCRN, and {list(data_origin_frequencies_MRI)[2]} ({list(data_origin_proportions_MRI)[2]}) MRIs from BCH.")








##  SPLIT THE DATASET INTO TRAIN VALIDATION AND TEST SETS

# Identify patients with more than 1 MRI
patients_with_more_than_1_MRI = CNN_data_no_duplicated[CNN_data_no_duplicated.duplicated('PatientID')]['PatientID'].drop_duplicates()

# Identify patients with only 1 MRI
patients_with_only_1_MRI = CNN_data_no_duplicated[~CNN_data_no_duplicated['PatientID'].isin(patients_with_more_than_1_MRI)]['PatientID']

# Split the patients with only 1 MRI per patient into train, validation, and test sets
train_data, rest_data = train_test_split(patients_with_only_1_MRI, train_size=0.40, shuffle=True, random_state=123)

validation_data, test_data = train_test_split(rest_data, test_size=0.55, shuffle=True, random_state=123)

# Define the sets
train_data = list(train_data) + list(patients_with_more_than_1_MRI)
validation_data = list(validation_data)
test_data = list(test_data)
print(f"The length of the train data is: {len(train_data)} patients.")
print(f"The patients in the train data are: {train_data}.")
print(f"The length of the validation data is: {len(validation_data)} patients.")
print(f"The patients in the validation data are: {validation_data}.")
print(f"The length of the test data is: {len(test_data)} patients.")
print(f"The patients in the test data are: {test_data}.")








## DEMOGRAPHICS IN THE TRAIN SET

# Number of patients in the train set
number_of_patients_train = len(pd.unique(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['PatientID']))
print(f"The number of patients in the train set is: {number_of_patients_train}.")


# Number of MRIs in the train set
number_of_MRIs_train = len(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['PatientID'])
print(f"The number of MRIs is: {number_of_MRIs_train}.")


# Number of MRIs per patient in the train set 
number_of_MRIs_per_patient_train = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].groupby('PatientID').size().value_counts()
number_of_MRIs_per_patient_proportion_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].groupby('PatientID').size().value_counts(normalize=True), decimals=3)
print(f"The number of MRIs per patient is: {number_of_MRIs_per_patient_train[1]} ({number_of_MRIs_per_patient_proportion_train[1]}) patients had 1 MRI, {number_of_MRIs_per_patient_train[2]} ({number_of_MRIs_per_patient_proportion_train[2]}) patients had 2 MRIs, and {number_of_MRIs_per_patient_train[3]} ({number_of_MRIs_per_patient_proportion_train[3]}) patients had 3 MRIs.")


# Calculate age statistics in the train set
age_median_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['age_at_MRI'].median(), decimals=1)
age_quantile_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['age_at_MRI'].quantile([0.25, 0.75]), decimals=1)
age_mean_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['age_at_MRI'].mean(), decimals=1)
age_standard_deviation_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['age_at_MRI'].std(), decimals=1)
print(f"The median (p25-p75) age at MRI is: {age_median_train} ({list(age_quantile_train)[0]}-{list(age_quantile_train)[1]}) years.")
print(f"The mean (standard deviation) age at MRI is: {age_mean_train} ({age_standard_deviation_train}) years.")


# Calculate sex statistics in the train set
sex_frequencies_train = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts()
sex_proportions_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts(normalize=True), decimals=3)
print(f"The sex distribution of the patients is: {list(sex_frequencies_train)[0]} ({list(sex_proportions_train)[0]}) males and {list(sex_frequencies_train)[1]} ({list(sex_proportions_train)[1]}) females.")


# Calculate origin of the dataset statistics in the train set
data_origin_frequencies_train = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].drop_duplicates('PatientID')['Original data set'].value_counts()
data_origin_proportions_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)].drop_duplicates('PatientID')['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_train)[0]} ({list(data_origin_proportions_train)[0]}) patients from TACERN, {list(data_origin_frequencies_train)[1]} ({list(data_origin_proportions_train)[1]}) patients from RDCRN, and {list(data_origin_frequencies_train)[2]} ({list(data_origin_proportions_train)[2]}) patients from BCH.")


# Calculate origin of the dataset MRI statistics in the train set
data_origin_frequencies_MRI_train = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['Original data set'].value_counts()
data_origin_proportions_MRI_train = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_MRI_train)[0]} ({list(data_origin_proportions_MRI_train)[0]}) MRIs from TACERN, {list(data_origin_frequencies_MRI_train)[1]} ({list(data_origin_proportions_MRI_train)[1]}) MRIs from RDCRN, and {list(data_origin_frequencies_MRI_train)[2]} ({list(data_origin_proportions_MRI_train)[2]}) MRIs from BCH.")








## DEMOGRAPHICS IN THE VALIDATION SET

# Number of patients in the validation set
number_of_patients_validation = len(pd.unique(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['PatientID']))
print(f"The number of patients in the validation set is: {number_of_patients_validation}.")


# Number of MRIs in the validation set
number_of_MRIs_validation = len(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['PatientID'])
print(f"The number of MRIs is: {number_of_MRIs_validation}.")


# Number of MRIs per patient in the validation set 
number_of_MRIs_per_patient_validation = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].groupby('PatientID').size().value_counts()
number_of_MRIs_per_patient_proportion_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].groupby('PatientID').size().value_counts(normalize=True), decimals=3)
print(f"The number of MRIs per patient is: {number_of_MRIs_per_patient_validation[1]} ({number_of_MRIs_per_patient_proportion_validation[1]}) patients had 1 MRI.")


# Calculate age statistics in the validation set
age_median_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['age_at_MRI'].median(), decimals=1)
age_quantile_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['age_at_MRI'].quantile([0.25, 0.75]), decimals=1)
age_mean_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['age_at_MRI'].mean(), decimals=1)
age_standard_deviation_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['age_at_MRI'].std(), decimals=1)
print(f"The median (p25-p75) age at MRI is: {age_median_validation} ({list(age_quantile_validation)[0]}-{list(age_quantile_validation)[1]}) years.")
print(f"The mean (standard deviation) age at MRI is: {age_mean_validation} ({age_standard_deviation_validation}) years.")


# Calculate sex statistics in the validation set
sex_frequencies_validation = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts()
sex_proportions_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts(normalize=True), decimals=3)
print(f"The sex distribution of the patients is: {list(sex_frequencies_validation)[0]} ({list(sex_proportions_validation)[0]}) males and {list(sex_frequencies_validation)[1]} ({list(sex_proportions_validation)[1]}) females.")


# Calculate origin of the dataset statistics in the validation set
data_origin_frequencies_validation = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].drop_duplicates('PatientID')['Original data set'].value_counts()
data_origin_proportions_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)].drop_duplicates('PatientID')['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_validation)[0]} ({list(data_origin_proportions_validation)[0]}) patients from TACERN, {list(data_origin_frequencies_validation)[1]} ({list(data_origin_proportions_validation)[1]}) patients from RDCRN, and {list(data_origin_frequencies_validation)[2]} ({list(data_origin_proportions_validation)[2]}) patients from BCH.")


# Calculate origin of the dataset MRI statistics in the validation set
data_origin_frequencies_MRI_validation = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['Original data set'].value_counts()
data_origin_proportions_MRI_validation = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_MRI_validation)[0]} ({list(data_origin_proportions_MRI_validation)[0]}) MRIs from TACERN, {list(data_origin_frequencies_MRI_validation)[1]} ({list(data_origin_proportions_MRI_validation)[1]}) MRIs from RDCRN, and {list(data_origin_frequencies_MRI_validation)[2]} ({list(data_origin_proportions_MRI_validation)[2]}) MRIs from BCH.")








## DEMOGRAPHICS IN THE TEST SET

# Number of patients in the test set
number_of_patients_test = len(pd.unique(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['PatientID']))
print(f"The number of patients in the test set is: {number_of_patients_test}.")


# Number of MRIs in the test set
number_of_MRIs_test = len(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['PatientID'])
print(f"The number of MRIs is: {number_of_MRIs_test}.")


# Number of MRIs per patient in the test set 
number_of_MRIs_per_patient_test = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].groupby('PatientID').size().value_counts()
number_of_MRIs_per_patient_proportion_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].groupby('PatientID').size().value_counts(normalize=True), decimals=3)
print(f"The number of MRIs per patient is: {number_of_MRIs_per_patient_test[1]} ({number_of_MRIs_per_patient_proportion_test[1]}) patients had 1 MRI.")


# Calculate age statistics in the test set
age_median_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['age_at_MRI'].median(), decimals=1)
age_quantile_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['age_at_MRI'].quantile([0.25, 0.75]), decimals=1)
age_mean_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['age_at_MRI'].mean(), decimals=1)
age_standard_deviation_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['age_at_MRI'].std(), decimals=1)
print(f"The median (p25-p75) age at MRI is: {age_median_test} ({list(age_quantile_test)[0]}-{list(age_quantile_test)[1]}) years.")
print(f"The mean (standard deviation) age at MRI is: {age_mean_test} ({age_standard_deviation_test}) years.")


# Calculate sex statistics in the test set
sex_frequencies_test = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts()
sex_proportions_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].drop_duplicates('PatientID')['male_sex_at_birth'].value_counts(normalize=True), decimals=3)
print(f"The sex distribution of the patients is: {list(sex_frequencies_test)[0]} ({list(sex_proportions_test)[0]}) males and {list(sex_frequencies_test)[1]} ({list(sex_proportions_test)[1]}) females.")


# Calculate origin of the dataset statistics in the test set
data_origin_frequencies_test = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].drop_duplicates('PatientID')['Original data set'].value_counts()
data_origin_proportions_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)].drop_duplicates('PatientID')['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_test)[0]} ({list(data_origin_proportions_test)[0]}) patients from TACERN, {list(data_origin_frequencies_test)[1]} ({list(data_origin_proportions_test)[1]}) patients from RDCRN, and {list(data_origin_frequencies_test)[2]} ({list(data_origin_proportions_test)[2]}) patients from BCH.")


# Calculate origin of the dataset MRI statistics in the test set
data_origin_frequencies_MRI_test = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['Original data set'].value_counts()
data_origin_proportions_MRI_test = np.round(CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['Original data set'].value_counts(normalize=True), decimals=3)
print(f"The origin of the data is: {list(data_origin_frequencies_MRI_test)[0]} ({list(data_origin_proportions_MRI_test)[0]}) MRIs from TACERN, {list(data_origin_frequencies_MRI_test)[1]} ({list(data_origin_proportions_MRI_test)[1]}) MRIs from RDCRN, and {list(data_origin_frequencies_MRI_test)[2]} ({list(data_origin_proportions_MRI_test)[2]}) MRIs from BCH.")








## STATISTICAL COMPARISONS BETWEEN THE TRAIN, VALIDATION, AND TEST SETS

# Sex distribution
sex_distribution = np.array([
    [sex_frequencies_train[0], sex_frequencies_validation[0], sex_frequencies_test[0]],
    [sex_frequencies_train[1], sex_frequencies_validation[1], sex_frequencies_test[1]]
    ])
print(f"The sex distribution (first row males, second row females; columns: train, validation, test) is: {sex_distribution})")

sex_chi2, sex_p_value, sex_dof, sex_expected_freq = chi2_contingency(sex_distribution)
print(f"The Chi-square test for the sex distribution is: {sex_chi2} and the p-values is {sex_p_value}).")


# Origin distribution
origin_distribution = np.array([
    [data_origin_frequencies_train[0], data_origin_frequencies_validation[0], data_origin_frequencies_test[0]],
    [data_origin_frequencies_train[1], data_origin_frequencies_validation[1], data_origin_frequencies_test[1]],
    [data_origin_frequencies_train[2], data_origin_frequencies_validation[2], data_origin_frequencies_test[2]]
    ])
print(f"The origin distribution (first row TACERN, second row RDCRN, third row BCH; columns: train, validation, test) is: {origin_distribution})")

origin_chi2, origin_p_value, origin_dof, origin_expected_freq = chi2_contingency(origin_distribution)
print(f"The Chi-square test for the origin distribution is: {origin_chi2} and the p-values is {origin_p_value}).")


# Number of MRI per patient distribution
number_MRI_per_patient_distribution = np.array([
    [number_of_MRIs_per_patient_train[1], number_of_MRIs_per_patient_validation[1], number_of_MRIs_per_patient_test[1]],
    [number_of_MRIs_per_patient_train[2], 0, 0],
    [number_of_MRIs_per_patient_train[3], 0, 0]
    ])
print(f"The origin distribution (first row TACERN, second row RDCRN, third row BCH; columns: train, validation, test) is: {number_MRI_per_patient_distribution})")

number_MRI_per_patient_chi2, number_MRI_per_patient_p_value, number_MRI_per_patient_dof, number_MRI_per_patient_expected_freq = chi2_contingency(number_MRI_per_patient_distribution)
print(f"The Chi-square test for the number of MRI per patient distribution is: {number_MRI_per_patient_chi2} and the p-values is {number_MRI_per_patient_p_value}).")


# Age distribution
age_distribution_train = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(train_data)]['age_at_MRI']
age_distribution_validation = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(validation_data)]['age_at_MRI']
age_distribution_test = CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)]['age_at_MRI']
print(f"The median age (train, validation, test) is: {age_distribution_train.median()}, {age_distribution_validation.median()}, {age_distribution_test.median()}")

age_kruskal_wallis, age_p_value = kruskal(age_distribution_train, age_distribution_validation, age_distribution_test)
print(f"The Kruskal-Wallis test for age at first MRI is: {age_kruskal_wallis} and the p-values is {age_p_value}).")


# Origin MRI distribution
origin_MRI_distribution = np.array([
    [data_origin_frequencies_MRI_train[0], data_origin_frequencies_MRI_validation[0], data_origin_frequencies_MRI_test[0]],
    [data_origin_frequencies_MRI_train[1], data_origin_frequencies_MRI_validation[1], data_origin_frequencies_MRI_test[1]],
    [data_origin_frequencies_MRI_train[2], data_origin_frequencies_MRI_validation[2], data_origin_frequencies_MRI_test[2]]
    ])
print(f"The origin distribution of the MRIs (first row TACERN, second row RDCRN, third row BCH; columns: train, validation, test) is: {origin_MRI_distribution})")

origin_MRI_chi2, origin_MRI_p_value, origin_MRI_dof, origin_MRI_expected_freq = chi2_contingency(origin_MRI_distribution)
print(f"The Chi-square test for the origin of the MRI distribution is: {origin_MRI_chi2} and the p-values is {origin_MRI_p_value}).")




# Adjustment of p-values for false discovery rate (Benjamini and Hochberg)
# These are p-values from the Tuber_burden script
tuber_burden_p_values_from_Table_1 = [0.00022406256410298044,
  0.0003412009310263858,
  0.002932956748843751,
  5.094392364520604e-05,
  0.0025055478492856066,
  0.2715493354351392,
  0.004602645895583667,
  0.0004417933037702567,
  0.11337257273296461,
  0.05727083050979645]
unadjusted_p_values = [sex_p_value, origin_p_value,number_MRI_per_patient_p_value, age_p_value, origin_MRI_p_value] + tuber_burden_p_values_from_Table_1
p_adjusted = false_discovery_control(unadjusted_p_values, method='bh') 
print(f"The p-values adjusted for multiple comparisons with the Benjamini-Hochberg method are: {p_adjusted}.")




# Extract some demographics for the peer-review analyses
CNN_data_no_duplicated.loc[CNN_data_no_duplicated['PatientID'].isin(test_data)][['PatientID', 'age_at_MRI', 'male_sex_at_birth', 'Original data set']].to_csv('extracted_data.csv', index=False)