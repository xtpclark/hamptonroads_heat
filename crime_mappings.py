# crime_mappings.py
# Maps real Norfolk crime types to simplified game categories

CRIME_TYPE_MAPPING = {
    # VIOLENT CRIMES
    'shooting': [
        'shooting',
        'shoot into occupied dwelling',
        'shoot into occupied vehicle',
        'reckless use of firearm'
    ],
    
    'homicide': [
        'homicide',
        'auto fatality',
        'undetermined death',
        'suicide'
    ],
    
    'assault': [
        'simple assault',
        'aggravated assault',
        'domestic-simple assault',
        'domestic-aggravated assault',
        'simple assault-leo',
        'sexual battery',
        'child abuse (misd)',
        'child endangerment'
    ],
    
    'robbery': [
        'robbery - business',
        'robbery - individual',
        'burglary - residence',
        'burglary - commercial',
        'burglary - nonresidence'
    ],
    
    # PROPERTY CRIMES
    'larceny_auto': [
        'larceny - from auto',
        'larceny - parts from auto',
        'stolen vehicle',
        'unauthorized use of vehicle',
        'recovered vehicle- stolen other jurisdiction'
    ],
    
    'petty_theft': [
        'shoplifting & concealment',
        'larceny (all others)',
        'larceny - from building',
        'larceny - of bicycle',
        'possess stolen property',
        'lost property'
    ],
    
    'vandalism': [
        'vandalism',
        'arson',
        'threat to burn'
    ],
    
    # DRUG/SOCIAL CRIMES
    'od': [
        'drug overdose',
        'od',
        'narcotic violations',
        'narcotics violations (felony)',
        'drug paraphernalia'
    ],
    
    # TRAFFIC/MISC
    'traffic': [
        'hit & run - property',
        'hit & run - personal injury',
        'driving under the influence (except marijuana)'
    ],
    
    # OTHER (catch-all for crimes that don't fit major categories)
    'other': [
        'all other offenses',
        'other crime offense',
        'runaway',
        'missing person',
        'natural death',
        'accidental injury',
        'trespassing',
        'disorderly conduct',
        'obstruct justice',
        'weapons violations (all others)',
        'concealed weapon',
        'brandishing firearm',
        'threaten bodily harm',
        'stalking',
        'harassment by computer',
        'obscene communications',
        'road rage threat',
        'identity theft',
        'fraud, false pretenses',
        'fraud, wire',
        'embezzlement',
        'rape',
        'forcible sodomy',
        'abduction',
        'prostitution, assisting/promoting',
        'indecent exposure',
        'bomb threat',
        'animal cruelty',
        'flight to avoid/fugitive'
    ]
}

def map_crime_type(original_type):
    """
    Convert a specific Norfolk crime type to a game category.
    
    Args:
        original_type: The crime type from the Norfolk dataset
        
    Returns:
        The simplified game category
    """
    original_lower = original_type.lower().strip()
    
    for game_type, real_types in CRIME_TYPE_MAPPING.items():
        if original_lower in [rt.lower() for rt in real_types]:
            return game_type
    
    # Default to 'other' if not found
    return 'other'

def get_crime_weight(crime_type):
    """
    Assign initial weight based on crime severity.
    
    Args:
        crime_type: The game category crime type
        
    Returns:
        Integer weight (1-10)
    """
    weights = {
        'homicide': 10,
        'shooting': 9,
        'assault': 7,
        'robbery': 7,
        'od': 6,
        'larceny_auto': 5,
        'vandalism': 4,
        'petty_theft': 3,
        'traffic': 3,
        'other': 2
    }
    
    return weights.get(crime_type, 5)

def analyze_dataset_coverage(df):
    """
    Analyze how well the mapping covers your actual dataset.
    
    Args:
        df: DataFrame with 'offense' column
        
    Returns:
        Dictionary with coverage statistics
    """
    import pandas as pd
    
    # Map all crimes
    df['game_type'] = df['offense'].apply(map_crime_type)
    
    # Calculate coverage
    coverage = df['game_type'].value_counts()
    unmapped = df[df['game_type'] == 'other']['offense'].value_counts()
    
    print("=== CRIME TYPE DISTRIBUTION ===")
    print(coverage)
    print("\n=== TOP UNMAPPED CRIMES ===")
    print(unmapped.head(10))
    
    return {
        'total_crimes': len(df),
        'mapped_distribution': coverage.to_dict(),
        'unmapped_count': len(df[df['game_type'] == 'other']),
        'coverage_percent': (1 - len(df[df['game_type'] == 'other']) / len(df)) * 100
    }
