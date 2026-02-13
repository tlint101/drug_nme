"""
Utility scripts
"""
# pull approved ligands from GTP
ligand_url = 'https://www.guidetopharmacology.org/services/ligands?type=Approved'

# pull data from GTP
GtoP = 'https://www.guidetopharmacology.org/services/'

# pull data from uniprot
uniprot_query = 'https://rest.uniprot.org/uniprotkb/'

# USFDA link
FDA_LANDING = "https://www.fda.gov/drugs/drug-approvals-and-databases/compilation-cder-new-molecular-entity-nme-drug-and-new-biologic-approvals"
DRUGS_FDA = f"https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
COL_TO_KEEP = ["Proprietary  Name", "Active Ingredient/Moiety", "NDA/BLA", "Route of Administration(1)",
               "FDA Approval Date", "Approval Year", "Orphan Drug Designation"]
NAMED_COLS = {'Proprietary  Name': 'Drug Name', 'Active Ingredient/Moiety': 'Active Ingredient',
              'FDA Approval Date': 'Approval Date', }
