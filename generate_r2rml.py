import pymysql
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the project-root .env file
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


connection = pymysql.connect(
    host=os.getenv("DB_HOST", "localhost"),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"]
)


# Read all tables from the insuka database
tables = pd.read_sql(
    """
    SELECT
        table_name
    FROM information_schema.tables
    WHERE table_schema = 'insuka'
      AND table_type = 'BASE TABLE'
    ORDER BY table_name;
    """,
    connection
)


print("Tables found in the database:")
print(tables.to_string(index=False))


# Read all columns and their datatypes
columns = pd.read_sql(
    """
    SELECT
        table_name,
        column_name,
        data_type,
        column_type,
        is_nullable,
        ordinal_position
    FROM information_schema.columns
    WHERE table_schema = 'insuka'
    ORDER BY table_name, ordinal_position;
    """,
    connection
)

print("\nColumns and datatypes found:")
print(columns.to_string(index=False))


# Read all primary keys
primary_keys = pd.read_sql(
    """
    SELECT
        table_name,
        column_name,
        ordinal_position
    FROM information_schema.key_column_usage
    WHERE table_schema = 'insuka'
      AND constraint_name = 'PRIMARY'
    ORDER BY table_name, ordinal_position;
    """,
    connection
)

print("\nPrimary keys found:")
print(primary_keys.to_string(index=False))


# Read all foreign keys
foreign_keys = pd.read_sql(
    """
    SELECT
        table_name,
        column_name,
        referenced_table_name,
        referenced_column_name,
        constraint_name
    FROM information_schema.key_column_usage
    WHERE table_schema = 'insuka'
      AND referenced_table_name IS NOT NULL
    ORDER BY table_name, column_name;
    """,
    connection
)

print("\nForeign keys found:")
print(foreign_keys.to_string(index=False))


# R2RML GENERATION

BASE_IRI = "https://tib.eu/insuka/"
OUTPUT_FILE = Path("mappings/generated_mapping.ttl")


def to_pascal_case(name):
    """
    method_properties -> MethodProperties
    test_methods      -> TestMethods
    """
    return "".join(
        word.capitalize()
        for word in name.split("_")
    )


def singularize(name):
    """
    Simple singularization rules.

    methods     -> method
    properties  -> property
    cities      -> city
    recipes     -> recipe
    """
    if name.endswith("ies"):
        return name[:-3] + "y"

    if name.endswith("ses"):
        return name[:-2]

    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]

    return name


def table_to_class(table_name):
    """
    method_properties -> MethodProperty
    methods           -> Method
    """
    words = table_name.split("_")

    singular_words = [
        singularize(word)
        for word in words
    ]

    return "".join(
        word.capitalize()
        for word in singular_words
    )


def table_to_path(table_name):
    """
    method_properties -> methodProperty
    test_methods      -> testMethod
    """
    class_name = table_to_class(table_name)

    return class_name[0].lower() + class_name[1:]


def column_to_predicate(column_name):
    """
    created_at  -> createdAt
    is_required -> isRequired
    """
    words = column_name.split("_")

    return (
        words[0]
        + "".join(
            word.capitalize()
            for word in words[1:]
        )
    )


def mysql_to_xsd(data_type, column_type):
    """
    Convert MySQL datatypes to RDF/XSD datatypes.
    """

    data_type = str(data_type).lower()
    column_type = str(column_type).lower()

    # MySQL often represents BOOLEAN as TINYINT(1)
    if data_type == "tinyint" and column_type.startswith("tinyint(1)"):
        return "xsd:boolean"

    datatype_mapping = {
        "tinyint": "xsd:integer",
        "smallint": "xsd:integer",
        "mediumint": "xsd:integer",
        "int": "xsd:integer",
        "integer": "xsd:integer",
        "bigint": "xsd:integer",

        "decimal": "xsd:decimal",
        "numeric": "xsd:decimal",
        "float": "xsd:float",
        "double": "xsd:double",

        "date": "xsd:date",
        "datetime": "xsd:dateTime",
        "timestamp": "xsd:dateTime",
        "time": "xsd:time",

        "boolean": "xsd:boolean",
        "bool": "xsd:boolean",

        "char": "xsd:string",
        "varchar": "xsd:string",
        "tinytext": "xsd:string",
        "text": "xsd:string",
        "mediumtext": "xsd:string",
        "longtext": "xsd:string"
    }

    return datatype_mapping.get(data_type)


# Create a dictionary:
# table name -> list of primary-key columns
primary_key_map = {}

for _, row in primary_keys.iterrows():

    table_name = row["table_name"]
    column_name = row["column_name"]

    if table_name not in primary_key_map:
        primary_key_map[table_name] = []

    primary_key_map[table_name].append(column_name)


# Create a lookup for foreign-key columns
foreign_key_columns = set()

for _, row in foreign_keys.iterrows():

    foreign_key_columns.add(
        (
            row["table_name"],
            row["column_name"]
        )
    )


# R2RML prefixes
mapping_lines = [
    "@base <http://example.com/rml/> .",
    "",
    "@prefix rr:   <http://www.w3.org/ns/r2rml#> .",
    "@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .",
    "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
    "@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .",
    "",
    f"@prefix ex: <{BASE_IRI}> .",
    ""
]


# Generate one TriplesMap for every database table
for table_name in tables["table_name"]:

    #if table_name == "charts":
       # continue
    triples_map_name = (
        to_pascal_case(table_name) + "TM"
    )

    class_name = table_to_class(table_name)

    subject_path = table_to_path(table_name)

    primary_key_columns = primary_key_map.get(
        table_name,
        []
    )


    # Use the primary key in the subject IRI
    if primary_key_columns:

        template_values = "/".join(
            "{" + column + "}"
            for column in primary_key_columns
        )

    else:

        # Temporary fallback for tables without a primary key
        template_values = "{id}"


    mapping_lines.extend([
        "",
        f"# {table_name}",
        "",
        f"<#{triples_map_name}>",
        "    a rr:TriplesMap ;",
        "",
        "    rr:logicalTable ["
    ])

    if table_name == "charts":
        mapping_lines.append(
            '        rr:sqlQuery """'
            'SELECT '
            'id, name, description, data, config, label, '
            'chartgable_id, chartgable_type, created_at, updated_at '
            'FROM charts'
            '"""'
        )
    else:
        mapping_lines.append(
            f'        rr:tableName "{table_name}"'
        )

    mapping_lines.extend([
        "    ] ;",
        "",
        "    rr:subjectMap [",
        (
            f'        rr:template '
            f'"{BASE_IRI}{subject_path}/'
            f'{template_values}" ;'
        ),
        f"        rr:class ex:{class_name}",
        "    ] ;"
    ])


    # Get all columns belonging to the current table
    table_columns = columns[
        columns["table_name"] == table_name
    ]


    # Generate literal mappings
    for _, column in table_columns.iterrows():

        column_name = column["column_name"]

        # Temporarily exclude only processed_data from charts
        if (
            table_name == "charts"
            and column_name == "processed_data"
        ):
            continue

        # Do not generate literals for primary keys
        if column_name in primary_key_columns:
            continue

        # Foreign keys will become relationships
        if (
            table_name,
            column_name
        ) in foreign_key_columns:
            continue


        predicate = column_to_predicate(
            column_name
        )

        datatype = mysql_to_xsd(
            column["data_type"],
            column["column_type"]
        )


        mapping_lines.extend([
            "",
            "    rr:predicateObjectMap [",
            f"        rr:predicate ex:{predicate} ;",
            "",
            "        rr:objectMap [",
            f'            rr:column "{column_name}"'
        ])


        if datatype:

            mapping_lines[-1] += " ;"

            mapping_lines.append(
                f"            rr:datatype {datatype}"
            )


        mapping_lines.extend([
            "        ]",
            "    ] ;"
        ])


    # Generate foreign-key relationships
    table_foreign_keys = foreign_keys[
        foreign_keys["table_name"] == table_name
    ]


    for _, foreign_key in table_foreign_keys.iterrows():

        child_column = (
            foreign_key["column_name"]
        )

        parent_table = (
            foreign_key["referenced_table_name"]
        )

        parent_column = (
            foreign_key["referenced_column_name"]
        )


        parent_triples_map = (
            to_pascal_case(parent_table)
            + "TM"
        )


        parent_class = table_to_class(
            parent_table
        )


        relationship_predicate = (
            "belongsTo"
            + parent_class
        )


        mapping_lines.extend([
            "",
            "    rr:predicateObjectMap [",
            (
                f"        rr:predicate "
                f"ex:{relationship_predicate} ;"
            ),
            "",
            "        rr:objectMap [",
            (
                f"            rr:parentTriplesMap "
                f"<#{parent_triples_map}> ;"
            ),
            "",
            "            rr:joinCondition [",
            (
                f'                rr:child '
                f'"{child_column}" ;'
            ),
            (
                f'                rr:parent '
                f'"{parent_column}"'
            ),
            "            ]",
            "        ]",
            "    ] ;"
        ])


    # Replace the final semicolon with a period
    mapping_lines[-1] = (
        mapping_lines[-1][:-1] + "."
    )


# Create the mappings directory if necessary
OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)


# Write the generated R2RML mapping
OUTPUT_FILE.write_text(
    "\n".join(mapping_lines),
    encoding="utf-8"
)


print(
    f"\nR2RML mapping generated successfully:"
    f"\n{OUTPUT_FILE}"
)


# Close the database connection
connection.close()