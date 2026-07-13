from flask import Flask, request, render_template, jsonify, current_app
import pandas as pd
import os
import time
import requests
import subprocess

import sys
from pathlib import Path


def generate_output_filename(input_filename):
    """
    Generate a dynamic output file name for the processed file.
    The output file name will be based on the original file name and a timestamp.
    """
    base_name, ext = os.path.splitext(input_filename)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    ext = ".csv"
    return f"{base_name}_processed_{timestamp}{ext}"


def readIndivSheetsTransformToCSV(all_sheets,templateMeasurementCSVFile):
    sheetIndex = 0
    for sheet_name, df in all_sheets.items():
        if sheetIndex > 0:
            #print(f"Sheet name: {sheet_name}")
            ##print(df.head())  # Print the first few rows of each DataFrame
            ##print("-" * 40)

            #Transform each sheet from 2nd sheet in SSBR_Requests.xlsx

            #Drop irrelevant columns
            df.drop(['SecondColumn', 'Comments'], axis=1, inplace=True)

            #Rename
            df_indivRecipeSheet_csvMeasurements = pd.read_csv(templateMeasurementCSVFile)

            colNames = df.columns.values
            #print("Names of columns in this sheet: " ,colNames)
            lenTotalColumns = len(colNames)
            recipeNames = colNames[2:lenTotalColumns]
            numRecipes = len(recipeNames)
            #print("Number of recipes here in this sheet: ",numRecipes)

            currentNumRowsInDf = df.shape[0]
            #print("number of rows: ",currentNumRowsInDf)


            df_sheet1_csvMeasurements = pd.read_csv(templateMeasurementCSVFile)

            idxForRow = 0
            totalRows = currentNumRowsInDf * numRecipes
            #print("Total rows in new df is ",totalRows)
            #print("-" * 40)

            # To transform each sheet into templateMeasurementCSVFile format
            incrementValRow = 0

            for index,row in df.iterrows():

                recipeNamesIdx = 0
                for incrementVal in range(0,numRecipes):
                    # check the number of recipes before
                    if recipeNamesIdx < numRecipes:
                        colNameIsAbout = recipeNames[recipeNamesIdx]
                        #print("Is about: ",recipeNames[recipeNamesIdx])
                        #print("Qual meas of ",row['FirstColumn'])
                        #print("specified numeric value ",row[colNameIsAbout])
                        #print("Unit: ",row['Units'])
                        #print("new row number where we write ",incrementValRow)
                        df_sheet1_csvMeasurements.loc[incrementValRow,'is_quality_measurement_of'] = row['FirstColumn']
                        df_sheet1_csvMeasurements.loc[incrementValRow,'has_specified_numeric_value'] = row[colNameIsAbout]
                        df_sheet1_csvMeasurements.loc[incrementValRow,'is_about'] = colNameIsAbout
                        df_sheet1_csvMeasurements.loc[incrementValRow,'has_measurement_unit_label'] = row['Units']
                        incrementValRow = incrementValRow + 1
                        recipeNamesIdx = recipeNamesIdx + 1
                    #incrementValRow = incrementValRow + currentNumRowsInDf
            #Write to CSV
            fileNameStr = sheet_name

            #output_filename = generate_output_filename(fileNameStr)
            #output_filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)
            #outputCSVFilePath = "output\\"+fileNameStr+"transformedCSV.csv"
            #df_sheet1_csvMeasurements.to_csv(output_filepath,sep=',', index=False, encoding='utf-8')
            
            # Append to ONE combined CSV (same schema, no extra columns)
            all_csv_path = os.path.join(
            current_app.config['OUTPUT_FOLDER'],
            "all_measurements.csv"
            )

            write_header = not os.path.exists(all_csv_path)

            df_sheet1_csvMeasurements.to_csv(
            all_csv_path,
            mode="a",
            header=write_header,
            index=False,
            encoding="utf-8"
            )


            #df
        else:
            sheetIndex = sheetIndex + 1


def preprocessSSBRRequestsFile(dataFileExcel,templateMeasurementCSVFile):
    #print("Preprocessing file: ",dataFileExcel)
    all_sheets = pd.read_excel(dataFileExcel, sheet_name=None)
    ##print(all_sheets[0])

    df_sheet1 = all_sheets['Summary']
    ##print("Sheet names: ",all_sheets.sheet_names)
    #print(df_sheet1)



    #Drop irrelevant columns
    df_sheet1.drop(['Mooney_Poly', 'MSR_Poly','Mooney_Step1', 'MSR_Step1', 'Mooney_End','MSR_End','Tg'], axis=1, inplace=True)

    #print(df_sheet1)

    #Rename columns
    dictColNamesRename = {'Request_No': 'Compound Number', 'Polymer_Names': 'Polymer Name', 'Mooney_Stripped': 'Mooney Viscosity', 'MSR_Stripped': 'Mooney Stress Relaxation', 'TgStr': 'Glass Transition Temperature','Mn': 'Number Averaged Molecular Weight', 'Mw': 'Weight Averaged Molecular Weight'}
    df_sheet1.rename(columns=dictColNamesRename,inplace=True)
    df_sheet1['Polymer Name'] = df_sheet1['Polymer Name'].str.replace(r'\s+', '', regex=True)
    df_sheet1['SampleName'] = df_sheet1['Polymer Name'].astype(str) + '_'+df_sheet1['Compound Number'].astype(str)

    #Remove duplicate rows based on column - Polymer Name
    ##df_sheet1.drop_duplicates(subset=['Polymer Name'], keep="first")

    #print(df_sheet1)

    #Add functionalization code from file - fx_SSBR
    #Commenting below lines as fx info included in current SSBR input file
    #df_sheet1_fx = pd.read_excel(fxFile, sheet_name='Sheet1')
    #df_sheet1_fx['Polymer Name'] = df_sheet1_fx['Polymer']
    #Get functionalization codes from fx_SBBR excel file
    #key_list = df_sheet1_fx['Polymer Name']
    #val_list = df_sheet1_fx['Functionalization (fx)']
    #Prepare dict to map functionalization codes to df_sheet1
    #dict_fx = dict(zip(key_list,val_list ))
    #print(dict_fx)
    #df_sheet1['Functionalization (fx)'] = df_sheet1['Polymer Name'].map(dict_fx)
    #print(df_sheet1)
    df_sheet1.loc[df_sheet1["fx"] == "0", "fx"] = ""
    df_sheet1.loc[df_sheet1["fx"] == "Empty", "fx"] = ""
    #df_sheet1.to_csv('output/outputPreprocessing/df_sheet1.csv',sep=',', index=False, encoding='utf-8')

    # Fill df_sheet1 in template format for measurement

    # Read each column from df_sheet1 - make DQ checks
    # Fill in template.csv - Prepare df_sheet1_template_filled and save in template.csv

    #Check if Compound Number is empty in any cell
    numEmptyValues = df_sheet1['Compound Number'].isnull().sum()

    #Get unique Compound Numbers in a list
    listCompoundNumbers = df_sheet1['SampleName'].tolist()
    #Column names from D to L represent qualities
    colNames = df_sheet1.columns.values
    #print(colNames)
    lenTotalColumns = len(colNames)
    qualityNames = colNames[4:lenTotalColumns-1]
    #print(qualityNames)
    lenQualityNames = len(qualityNames)
    #print(lenQualityNames)
    lenCompoundNumbers = df_sheet1.shape[0]
    #print("number of rows: ",lenCompoundNumbers)
    #print(numEmptyValues)
    if numEmptyValues == 0:
        #Compound Number is non empty
        df_sheet1_csvMeasurements = pd.read_csv(templateMeasurementCSVFile)

        #Compound Number is the Object (pmd:Object)
        #for j in range(0,lenCompoundNumbers):
        idxForRow = 0
        totalRows = lenCompoundNumbers * lenQualityNames
        #print("Total rows ", totalRows)

        #print("________________ Before choosing columns __________________")
        #print(df_sheet1)
        #print("___________________________________")

        df_sheet1 = df_sheet1[['Mooney Viscosity','Mooney Stress Relaxation','Styrene_Cont','Cis_Cont','Trans_Cont','Vinyl_Cont','Glass Transition Temperature','Number Averaged Molecular Weight','Weight Averaged Molecular Weight','SampleName']]
        #print("___________ After choosing columns ________________________")
        #print(df_sheet1)
        #print("___________________________________")

        colListOfQualityMeasurements = ['Mooney Viscosity','Mooney Stress Relaxation','Styrene_Cont','Cis_Cont','Trans_Cont','Vinyl_Cont','Glass Transition Temperature','Number Averaged Molecular Weight','Weight Averaged Molecular Weight']
        incrementValue = 0
        for index,row in df_sheet1.iterrows():
            #Debug statements for print below
            #if incrementValue == 0:
            #print("Each row : ",row)
            #print("index: ",index)
            #print("incrementValue value before writing ",incrementValue)
            #print("Mooney Viscosity: ",row["Mooney Viscosity"])


            ##compPoly = df_sheet1.loc[incrementValue,'SampleName']
            compPoly = row['SampleName']
            ##k = incrementValue+lenQualityNames-1
            #isAbout = df_sheet1_csvMeasurements.loc[incrementValue,'is_about']
            #isAbout = df_sheet1_csvMeasurements['is_about'].loc[df_sheet1_csvMeasurements.index[incrementValue]]
            #print("compPoly is ",compPoly)
            #print("isAbout is ",isAbout)
            #if(compPoly==isAbout):
            #print("Correct row to write")
            df_sheet1_csvMeasurements.loc[incrementValue,'has_specified_numeric_value'] = row["Mooney Viscosity"]
            df_sheet1_csvMeasurements.loc[incrementValue,'is_quality_measurement_of'] = "Mooney Viscosity"
            df_sheet1_csvMeasurements.loc[incrementValue,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+1,'has_specified_numeric_value'] = row["Mooney Stress Relaxation"]
            df_sheet1_csvMeasurements.loc[incrementValue+1,'is_quality_measurement_of'] = "Mooney Stress Relaxation"
            df_sheet1_csvMeasurements.loc[incrementValue+1,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+2,'has_specified_numeric_value'] = row["Styrene_Cont"]
            df_sheet1_csvMeasurements.loc[incrementValue+2,'is_quality_measurement_of'] = "Styrene_Cont"
            df_sheet1_csvMeasurements.loc[incrementValue+2,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+3,'has_specified_numeric_value'] = row["Cis_Cont"]
            df_sheet1_csvMeasurements.loc[incrementValue+3,'is_quality_measurement_of'] = "Cis_Cont"
            df_sheet1_csvMeasurements.loc[incrementValue+3,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+4,'has_specified_numeric_value'] = row["Trans_Cont"]
            df_sheet1_csvMeasurements.loc[incrementValue+4,'is_quality_measurement_of'] = "Trans_Cont"
            df_sheet1_csvMeasurements.loc[incrementValue+4,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+5,'has_specified_numeric_value'] = row["Vinyl_Cont"]
            df_sheet1_csvMeasurements.loc[incrementValue+5,'is_quality_measurement_of'] = "Vinyl_Cont"
            df_sheet1_csvMeasurements.loc[incrementValue+5,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+6,'has_specified_numeric_value'] = row["Glass Transition Temperature"]
            df_sheet1_csvMeasurements.loc[incrementValue+6,'is_quality_measurement_of'] = "Glass Transition Temperature"
            df_sheet1_csvMeasurements.loc[incrementValue+6,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+7,'has_specified_numeric_value'] = row["Number Averaged Molecular Weight"]
            df_sheet1_csvMeasurements.loc[incrementValue+7,'is_quality_measurement_of'] = "Number Averaged Molecular Weight"
            df_sheet1_csvMeasurements.loc[incrementValue+7,'is_about'] = row['SampleName']
            df_sheet1_csvMeasurements.loc[incrementValue+8,'has_specified_numeric_value'] = row["Weight Averaged Molecular Weight"]
            df_sheet1_csvMeasurements.loc[incrementValue+8,'is_quality_measurement_of'] = "Weight Averaged Molecular Weight"
            df_sheet1_csvMeasurements.loc[incrementValue+8,'is_about'] = row['SampleName']
            incrementValue = incrementValue+lenQualityNames
            ##else:
            ##print("incorrect row")
            ##print("Value of incrementValue before increment is ",incrementValue)
            ##incrementValue = incrementValue+lenQualityNames

        #print("--------------------------------------------")
        #print("Before wrting to csv file")
        #print(df_sheet1_csvMeasurements)
        #print("--------------------------------------------")


        # Get filename and extension separately
        inputFileName, ext = os.path.splitext(os.path.basename(dataFileExcel))

        # Get filename without extension
        inputFileNameOnly = inputFileName.split('.')[0]
        #output_filename = generate_output_filename(inputFileNameOnly)
        #output_filepath = os.path.join(current_app.config['OUTPUT_FOLDER'], output_filename)

        #df_sheet1_csvMeasurements.to_csv(output_filepath,sep=',', index=False, encoding='utf-8')
        
        # Append Summary data to ONE combined CSV
        all_csv_path = os.path.join(
        current_app.config['OUTPUT_FOLDER'],
        "all_measurements.csv"
        )

        write_header = not os.path.exists(all_csv_path)

        df_sheet1_csvMeasurements.to_csv(
        all_csv_path,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8"
        )


        #Rest of the sheets - transformation
        readIndivSheetsTransformToCSV(all_sheets,templateMeasurementCSVFile)




def upload_to_graphdb(repo_url, ttl_file_path, username=None, password=None):
    """
    Securely uploads a TTL file to a specified GraphDB repository.

    Args:
        repo_url (str): The base URL of the GraphDB repository.
        ttl_file_path (str): Path to the TTL file to upload.
        username (str, optional): Username for GraphDB authentication.
        password (str, optional): Password for GraphDB authentication.

    Raises:
        Exception: If the upload fails.
    """
    with open(ttl_file_path, 'rb') as ttl_file:
        headers = {'Content-Type': 'application/x-turtle'}
        auth = (username, password) if username and password else None
        response = requests.post(
            f"{repo_url}/statements",
            data=ttl_file,
            headers=headers,
            auth=auth
        )
    if response.status_code != 204:
        raise Exception(
            f"Failed to upload {ttl_file_path}. Status code: {response.status_code}, Response: {response.text}"
        )
    print(f"Securely uploaded {ttl_file_path} to GraphDB.")

from urllib.parse import urlencode

def run_sparql_query(repository_url, query, username=None, password=None):
    headers = {
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    auth = (username, password) if username and password else None
    data = {"query": query}  # Send as form-encoded data

    print(f"Sending request to: {repository_url}")
    print(f"Headers: {headers}")
    print(f"Query: {query}")

    try:
        response = requests.post(repository_url, headers=headers, data=data, auth=auth)

        print(f"Response Code: {response.status_code}")
        print(f"Response Content: {response.text}")

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"SPARQL query failed: HTTP {response.status_code}: {response.text}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"An error occurred while running the SPARQL query: {e}")


import os
from flask import current_app

def run_rmlmapper():
    jar_path = os.path.abspath(os.path.join(current_app.root_path, "..", "tools", "rmlmapper.jar"))

    mapping_path = os.path.abspath(os.path.join(current_app.root_path, "..", "mappings", "mapping.rml.ttl"))

    output_ttl = os.path.join(current_app.config["OUTPUT_GRAPH_FOLDER"], "rml_output.ttl")

    os.makedirs(current_app.config["OUTPUT_GRAPH_FOLDER"], exist_ok=True)

    cmd = [ "java", "-jar", jar_path, "-m", mapping_path, "-o", output_ttl]

    print("Running RMLMapper command:")
    print(" ".join(cmd))

    result = subprocess.run(cmd, capture_output=True, text=True)

    print("RMLMapper STDOUT:\n", result.stdout)
    print("RMLMapper STDERR:\n", result.stderr)

    if result.returncode != 0:
        raise RuntimeError("RMLMapper failed")

    return output_ttl

def ensure_graphdb_repository(
    repository_id,
    username=None,
    password=None
):
    """
    Checks whether a GraphDB repository exists.

    If the repository does not exist, it creates
    a new GraphDB repository automatically.
    """

    graphdb_base_url = "http://localhost:7200"

    repositories_url = (
        f"{graphdb_base_url}/rest/repositories"
    )

    auth = (
        (username, password)
        if username and password
        else None
    )

    print(
        f"Checking GraphDB repository: "
        f"{repository_id}"
    )

    # ---------------------------------------------
    # Check whether the repository already exists
    # ---------------------------------------------

    response = requests.get(
        repositories_url,
        auth=auth,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Could not retrieve the GraphDB "
            "repository list.\n"
            f"HTTP status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    repositories = response.json()

    repository_exists = any(
        repository.get("id") == repository_id
        for repository in repositories
    )

    if repository_exists:
        print(
            "GraphDB repository already exists:"
        )
        print(repository_id)

        return

    # Create the repository if it does not exist

    print(
        "GraphDB repository does not exist."
    )

    print(
        "Creating GraphDB repository:"
    )

    print(repository_id)

    repository_config = {
        "id": repository_id,
        "title": repository_id,
        "type": "graphdb",

        "params": {
            "defaultNS": {
                "name": "defaultNS",
                "label": (
                    "Default namespaces for imports "
                    "(';' delimited)"
                ),
                "value": ""
            },

            "queryTimeout": {
                "name": "queryTimeout",
                "label": "Query timeout",
                "value": "0"
            },

            "throwQueryEvaluationExceptionOnTimeout": {
                "name": (
                    "throwQueryEvaluationExceptionOnTimeout"
                ),
                "label": (
                    "Throw exception on query timeout"
                ),
                "value": "false"
            },

            "queryLimitResults": {
                "name": "queryLimitResults",
                "label": "Limit query results",
                "value": "0"
            }
        }
    }

    create_response = requests.post(
        repositories_url,
        json=repository_config,
        auth=auth,
        timeout=30
    )

    if create_response.status_code not in (
        200,
        201,
        204
    ):
        raise RuntimeError(
            "GraphDB repository creation failed.\n"
            f"HTTP status: "
            f"{create_response.status_code}\n"
            f"Response: "
            f"{create_response.text}"
        )

    print(
        "GraphDB repository created "
        "successfully:"
    )

    print(repository_id)


def run_r2rml_pipeline():
    """
    Runs the complete MySQL-to-GraphDB pipeline:

    1. Generates the R2RML mapping from the MySQL schema.
    2. Generates RDF from the generated R2RML mapping.
    3. Uploads the generated RDF file to GraphDB.

    Returns:
        str: Path to the generated RDF file.
    """

    # Project paths
    
    project_root = Path(__file__).resolve().parent.parent

    generator_script = (
        project_root
        / "generate_r2rml.py"
    )

    mapping_file = (
        project_root
        / "mappings"
        / "generated_mapping.ttl"
    )

    # RDF output generated by RMLMapper.
    rdf_file = (
        project_root
        / "output"
        / "output_graphs"
        / "generated_rdf.ttl"
    )

    rmlmapper_jar = (
        project_root
        / "tools"
        / "rmlmapper.jar"
    )

    # Check required input files

    if not generator_script.exists():
        raise FileNotFoundError(
            f"R2RML generator script was not found: "
            f"{generator_script}"
        )

    if not rmlmapper_jar.exists():
        raise FileNotFoundError(
            f"RMLMapper JAR file was not found: "
            f"{rmlmapper_jar}"
        )

    # Create the RDF output directory if it does not exist.
    rdf_file.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    # Step 1: Generate the R2RML mapping

    print("\n========================================")
    print("STEP 1: Generating the R2RML mapping")
    print("========================================")

    mapping_result = subprocess.run(
        [
            sys.executable,
            str(generator_script)
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True
    )

    # Display output produced by generate_r2rml.py.
    if mapping_result.stdout:
        print("\nR2RML generator output:")
        print(mapping_result.stdout)

    if mapping_result.stderr:
        print("\nR2RML generator error:")
        print(mapping_result.stderr)

    # Stop the pipeline if mapping generation failed.
    if mapping_result.returncode != 0:
        error_message = (
            mapping_result.stderr.strip()
            or mapping_result.stdout.strip()
            or "The R2RML generator did not provide an error message."
        )

        raise RuntimeError(
            f"R2RML mapping generation failed with "
            f"exit code {mapping_result.returncode}.\n\n"
            f"{error_message}"
        )

    # Verify that generate_r2rml.py created the mapping.
    if not mapping_file.exists():
        raise FileNotFoundError(
            f"The generated R2RML mapping was not found: "
            f"{mapping_file}"
        )

    print("\nR2RML mapping generated successfully:")
    print(mapping_file)

    # Step 2: Generate RDF using RMLMapper

    print("\n========================================")
    print("STEP 2: Generating RDF with RMLMapper")
    print("========================================")

    if rdf_file.exists():
        print("Removing the previous RDF output:")
        print(rdf_file)

        rdf_file.unlink()

    rmlmapper_command = [
        "java",
        "-jar",
        str(rmlmapper_jar),

        "-m",
        str(mapping_file),

        "-o",
        str(rdf_file),

        "-dsn",
        "jdbc:mysql://localhost:3306/insuka",

        "-u",
        "root",

        "-p",
        "NewPassword123!"
    ]

    print("\nRunning RMLMapper...")

    rmlmapper_result = subprocess.run(
        rmlmapper_command,
        cwd=str(project_root),
        capture_output=True,
        text=True
    )

    if rmlmapper_result.stdout:
        print("\nRMLMapper STDOUT:")
        print(rmlmapper_result.stdout)

    if rmlmapper_result.stderr:
        print("\nRMLMapper STDERR:")
        print(rmlmapper_result.stderr)

    # Stop the pipeline and display the real RMLMapper
    # error if the Java process fails.
    if rmlmapper_result.returncode != 0:
        error_message = (
            rmlmapper_result.stderr.strip()
            or rmlmapper_result.stdout.strip()
            or "RMLMapper did not provide an error message."
        )

        raise RuntimeError(
            f"RMLMapper failed with exit code "
            f"{rmlmapper_result.returncode}.\n\n"
            f"{error_message}"
        )

    # Verify that RMLMapper created the RDF file.
    if not rdf_file.exists():
        raise FileNotFoundError(
            f"RMLMapper completed without reporting an "
            f"error, but the generated RDF file was not "
            f"found: {rdf_file}"
        )

    # Check that the generated RDF file is not empty.
    if rdf_file.stat().st_size == 0:
        raise RuntimeError(
            f"RMLMapper created an empty RDF file: "
            f"{rdf_file}"
        )

    print("\nRDF generated successfully:")
    print(rdf_file)

    print(
        f"Generated RDF file size: "
        f"{rdf_file.stat().st_size:,} bytes"
    )

    # Step 3: Upload the RDF file to GraphDB

    print("\n========================================")
    print("STEP 3: Uploading RDF to GraphDB")
    print("========================================")


    # Read GraphDB settings from config.py.
    graphdb_repo = current_app.config[
        "GRAPHDB_REPO"
    ]


    username = current_app.config[
        "GRAPHDB_USERNAME"
    ]

    password = current_app.config[
        "GRAPHDB_PASSWORD"
    ]

    graphdb_repo_url = (
        f"http://localhost:7200/"
        f"repositories/"
        f"{graphdb_repo}"
    )


    print("Uploading generated RDF to:")
    print(
        f"{graphdb_repo_url}/statements"
    )


    # Upload the generated RDF once.
    upload_to_graphdb(
        graphdb_repo_url,
        str(rdf_file),
        username,
        password
    )


    print(
        "\nGenerated RDF uploaded to GraphDB "
        "successfully."
    )


    print("\n========================================")
    print("R2RML PIPELINE COMPLETED SUCCESSFULLY")
    print("========================================")

    # Return the generated RDF path to routes.py.
    return str(rdf_file)

