import pandas 

df = pandas.read_csv('all_extracted_contacts (2).csv')

df.to_excel('all_extracted_contacts (2).xlsx', index=False)