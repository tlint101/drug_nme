"""
Utility scripts
"""
import os
import re

# pull approved ligands from GTP
ligand_url = 'https://www.guidetopharmacology.org/services/ligands?type=Approved'

# pull data from GTP
GtoP = 'https://www.guidetopharmacology.org/services/'

# Guide to Pharmacology API key, sent as a request header. GtoP asks that keys stay out of urls and published code
GTOP_KEY_HEADER = 'GTP-API-Key'
GTOP_KEY_ENV = 'GTOP_API_KEY'

# pull data from uniprot
uniprot_query = 'https://rest.uniprot.org/uniprotkb/'

# USFDA link
FDA_LANDING = "https://www.fda.gov/drugs/drug-approvals-and-databases/compilation-cder-new-molecular-entity-nme-drug-and-new-biologic-approvals"
DRUGS_FDA = f"https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals"

# pull data from ClinicalTrials.gov
CTGOV = 'https://clinicaltrials.gov/api/v2/'

# max records from ClinicalTrials.gov
CTGOV_PAGE_SIZE = 1000

# clinical trials requested fields
TRIAL_FIELDS = ["NCTId", "BriefTitle", "OverallStatus", "Phase", "StudyType", "Condition", "InterventionName",
                "InterventionType", "LeadSponsorName", "EnrollmentCount", "StartDate", "CompletionDate"]

# valid enum values, from clinical trials
TRIAL_STATUS = ['ACTIVE_NOT_RECRUITING', 'COMPLETED', 'ENROLLING_BY_INVITATION', 'NOT_YET_RECRUITING', 'RECRUITING',
                'SUSPENDED', 'TERMINATED', 'WITHDRAWN', 'AVAILABLE', 'NO_LONGER_AVAILABLE',
                'TEMPORARILY_NOT_AVAILABLE', 'APPROVED_FOR_MARKETING', 'WITHHELD', 'UNKNOWN']
TRIAL_PHASES = ['NA', 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4']
TRIAL_TYPES = ['EXPANDED_ACCESS', 'INTERVENTIONAL', 'OBSERVATIONAL']

# kinase inhibitors that ChEMBL files under a non-kinase target, i.e. rapalogs act on mTOR through FKBP12
KINASE_OVERRIDE = ['sirolimus', 'everolimus', 'temsirolimus']

# USAN stems specific to kinase inhibitors, only used when ChEMBL has no data on a drug yet (recent approvals).
# Plain "nib" is not used, it also matches IDH (-sidenib) and farnesyltransferase (-farnib) inhibitors, nor "-anib",
# which covers any angiogenesis inhibitor, i.e. the aptamer pegaptanib
KINASE_STEMS = ['tinib', 'ciclib', 'fenib', 'lisib', 'metinib', 'sertib', 'rolimus']

# ChEMBL mechanism action types that count as inhibiting a kinase. Agonists, i.e. insulin on its receptor, do not
KINASE_ACTIONS = ['INHIBITOR', 'ANTAGONIST', 'ALLOSTERIC ANTAGONIST', 'NEGATIVE ALLOSTERIC MODULATOR',
                  'NEGATIVE MODULATOR', 'BLOCKER', 'INVERSE AGONIST', 'DEGRADER']

# radioisotope labels on diagnostic tracers, i.e. "florquinitau F 18"
RADIOLABEL = r'\s+(?:f|ga|tc|lu|i|cu|zr|in|y|ra|c|n|o|rb|tl|xe|sm|sr|ac|pb)[- ]?\d{1,3}m?$'

# strip salts
SALT_REMOVAL = [' sulfate', ' chloride', ' hydrochloride', ' sodium', ' potassium', ' mesylate', ' acetate',
                ' maleate']


def clean_drug_name(raw_name: str = None):
    """
    Clean an FDA active ingredient name so it can be matched against an external database. FDA names carry biologic
    suffixes, salt forms, and combination products that will not match on a plain search, i.e. "tarlatamab-dlle"
    becomes "tarlatamab" and "nirmatrelvir; ritonavir (co-packaged)" becomes "nirmatrelvir".

    :param raw_name: str
        The raw active ingredient name.
    """
    if not isinstance(raw_name, str) or not raw_name.strip():
        return None

    # strip hidden \xa0 space
    name = raw_name.replace('\xa0', ' ').strip().lower()

    # remove parentheses
    name = re.sub(r'\(.*?\)', '', name).strip()

    # keep first ingredient
    if ' and ' in name or ',' in name or ';' in name:
        name = name.replace(' and ', ',').replace(';', ',')
        name = name.split(',')[0].strip()

    # remove FDA biologic suffixes ("-abcd")
    name = re.sub(r'-[a-z]{4}$', '', name)

    # remove radioisotope labels
    name = re.sub(RADIOLABEL, '', name)

    # identify and remove potential salt name
    for salt in SALT_REMOVAL:
        if name.endswith(salt):
            name = name.replace(salt, '')

    return name.strip() or None

def gtop_headers(api_key: str = None):
    """
    Build the request header for the Guide to Pharmacology API. The key given to the class wins, otherwise it is read
    from the GTOP_API_KEY environment variable, so shared code does not need to hold the key.

    :param api_key: str
        A registered Guide to Pharmacology API key.
    """
    key = api_key or os.environ.get(GTOP_KEY_ENV)
    if not key:
        raise ValueError(f"Guide to Pharmacology requires an API key! Pass api_key= or set the {GTOP_KEY_ENV} "
                         f"environment variable. Register at https://www.guidetopharmacology.org/webServices.jsp")

    return {GTOP_KEY_HEADER: key}


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
COL_TO_KEEP = ["Proprietary  Name", "Active Ingredient/Moiety", "NDA/BLA", "Route of Administration(1)",
               "FDA Approval Date", "Approval Year", "Orphan Drug Designation"]
NAMED_COLS = {'Proprietary  Name': 'Drug Name', 'Active Ingredient/Moiety': 'Active Ingredient',
              'FDA Approval Date': 'Approval Date', }

# for drugs not found in ChEMBL
DRUG_OVERRIDE = {
    # Stubborn Biologics & Toxins
    'imetelstat': 'Oligonucleotide',
    'defibrotide sodium': 'Oligonucleotide',
    'letibotulinumtoxina': 'Protein',
    'letibotulinumtoxina-wlbg': 'Protein',
    'abobotulinumtoxina': 'Protein',
    'incobotulinumtoxina': 'Protein',
    'prabotulinumtoxina-xvfs': 'Protein',
    'daxibotulinumtoxina-lanm': 'Protein',

    # Antibodies & ADCs
    'garadacimab-gxii': 'Antibody',
    'fam-trastuzumab deruxtecan-nxki': 'Antibody',
    'muromonab-cd3': 'Antibody',

    # Recombinant Proteins, Peptides & Enzymes
    'calcitonin (human)': 'Protein',
    'lispro insulin': 'Protein',
    'mecasermin (rdna origin)': 'Protein',
    'mecasermin rinfabate (rdna origin)': 'Protein',
    'clostridial collagenase histolyticum': 'Protein',
    'asparaginase erwinia chrysanthemi (recombinant)-rywn': 'Protein',
    'teduglutide (rdna origin)': 'Protein',
    'aprotinin': 'Protein',
    'dasiglucagon': 'Protein',

    # Lung Surfactants (Lipid-Protein Complexes)
    'beractant': 'Protein',
    'calfactant': 'Protein',
    'poractant': 'Protein',
    'lucinactant': 'Protein',

    # Oligosaccharides / Sugars
    'danaparoid sodium': 'Oligosaccharide',
    'icodextrin': 'Oligosaccharide',

    # FDA Typos
    'clofarbine': 'Small molecule',
    'ibutilide fumurate': 'Small molecule',

    # Radiopharmaceuticals & Isotopes
    'iofetamine hydrochloride  i 123': 'Small molecule',
    'rubidium rb 82 chloride': 'Small molecule',
    'strontium 89 chloride': 'Small molecule',
    '13 c urea': 'Small molecule',
    '14 c urea': 'Small molecule',
    'choline c 11': 'Small molecule',
    'florbetaben f 18': 'Small molecule',
    'fluoroestradiol f 18': 'Small molecule',
    'copper cu 64 dotatate': 'Small molecule',
    'piflufolastat f 18': 'Small molecule',
    'xenon xe 129 hyperpolarized': 'Small molecule',

    # Complex Combination Drugs & specific salts
    'rimexalone': 'Small molecule',
    'biskalcitrate, metronidazole, tetracycline hydrochloride': 'Small molecule',
    'methylnaltrexone bromide': 'Small molecule',
    'estradiol valerate; estradiol valerate and dienogest': 'Small molecule',
    'cabotegravir; rilpivirine (co-packaged)': 'Small molecule',
    'vonoprazan; amoxicillin; clarithromycin (co-packaged)': 'Small molecule',
    'sulbactam; durlobactam (co-packaged)': 'Small molecule',
    'nirmatrelvir; ritonavir (co-packaged)': 'Small molecule',
    'conjugated estrogens and bazedoxifene': 'Small molecule',

    # Complex Polymers, Minerals, Extracts & Microspheres
    'perfluoroalkylpolyether, polytetrafluoroethylene': 'Small molecule',
    'perflutren lipid microsphere': 'Small molecule',
    'iotrolan': 'Small molecule',
    'iodixanol': 'Small molecule',
    'bentoquatam': 'Small molecule',
    'ferumoxides': 'Small molecule',
    'ferumoxsil': 'Small molecule',
    'sodium ferric gluconate complex': 'Small molecule',
    'monooctanoin': 'Small molecule',
    'ivermectin': 'Small molecule',
    'colesevelam hydrochloride': 'Small molecule',
    'kunecatechins': 'Small molecule',
    'fish oil triglycerides': 'Small molecule',

    # 2026 drugs, remove in future updates
    'milsaperidone': 'Small molecule',
    'copper histidinate': 'Small molecule',
}
