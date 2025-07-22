from pathlib import Path
from typing import List

import kuzu
import polars as pl


def process_condition_column(
    df: pl.DataFrame, column: str, separators: List[str] = [" or ", "/"], strip: bool = True
) -> pl.DataFrame:
    """
    Explode the condition column with multiple separators into multiple rows.
    """
    # Start with the initial dataframe
    result = df

    # Create expression for the initial transformation
    expr = pl.col(column).str.to_lowercase()

    # First transformation
    result = result.with_columns(expr.alias(column))

    # Process each separator with separate explode operations
    for separator in separators:
        result = result.with_columns(pl.col(column).str.split(separator)).explode(column)

    # Add stripping if needed
    if strip:
        result = result.with_columns(pl.col(column).str.strip_chars())

    return result


def create_node_tables(conn: kuzu.Connection) -> None:
    # Create drug and side effects graph
    conn.execute("""CREATE NODE TABLE IF NOT EXISTS DrugGeneric (name STRING PRIMARY KEY)""")
    conn.execute("""CREATE NODE TABLE IF NOT EXISTS DrugBrand (name STRING PRIMARY KEY)""")
    conn.execute("""CREATE NODE TABLE IF NOT EXISTS Symptom (name STRING PRIMARY KEY)""")
    conn.execute("""CREATE NODE TABLE IF NOT EXISTS Condition (name STRING PRIMARY KEY)""")


def create_rel_tables(conn) -> None:
    conn.execute("""CREATE REL TABLE IF NOT EXISTS CAN_CAUSE (FROM DrugGeneric TO Symptom)""")
    conn.execute("""CREATE REL TABLE IF NOT EXISTS HAS_BRAND (FROM DrugGeneric TO DrugBrand)""")
    conn.execute("""CREATE REL TABLE IF NOT EXISTS IS_TREATED_BY (FROM Condition TO DrugGeneric)""")


def merge_condition_nodes(df, conn) -> None:
    conditions_df = df.select(pl.col("condition")).unique()
    conn.execute(
        """
        LOAD FROM conditions_df
        MERGE (c:Condition {name: condition})
        """
    )
    print(f"Merged {len(conditions_df)} conditions into the graph")


def merge_symptom_nodes(df, conn) -> None:
    symptoms_df = df.select(
        pl.col("side_effects").explode().str.to_lowercase().alias("symptom")
    ).unique()
    conn.execute(
        """
        LOAD FROM symptoms_df
        MERGE (s:Symptom {name: symptom})
        """
    )
    print(f"Merged {len(symptoms_df)} symptoms into the graph")


def merge_generic_drug_nodes(df, conn) -> None:
    # Extract generic drug names from the nested structure
    generic_drugs_df = (
        df.explode("drug")
        .select(
            pl.col("drug").struct.field("generic_name").str.to_lowercase().alias("generic_names")
        )
        .unique()
    )
    conn.execute(
        """
        LOAD FROM generic_drugs_df
        MERGE (d:DrugGeneric {name: generic_names})
        """
    )
    print(f"Merged {len(generic_drugs_df)} generic drugs into the graph")


def merge_brand_drug_nodes(df, conn) -> None:
    # Extract brand drug names from the nested structure
    brand_drugs_df = (
        df.explode("drug")
        .select(pl.col("drug").struct.field("brand_names").alias("brand_names"))
        .explode("brand_names")
        .filter(pl.col("brand_names") != "")  # Filter out empty brand names
        .select(pl.col("brand_names").str.to_lowercase())
        .unique()
    )
    conn.execute(
        """
        LOAD FROM brand_drugs_df
        MERGE (d:DrugBrand {name: brand_names})
        """
    )
    print(f"Merged {len(brand_drugs_df)} brand drugs into the graph")


def merge_condition_generic_drug_rel(df, conn) -> None:
    condition_drug_df = (
        df.explode("drug").select(
            [
                pl.col("condition").str.to_lowercase().alias("condition"),
                pl.col("drug")
                .struct.field("generic_name")
                .str.to_lowercase()
                .alias("generic_name"),
            ]
        )
    ).unique()

    response = conn.execute(
        """
        LOAD FROM condition_drug_df
        MATCH (d:Condition {name: condition}), (g:DrugGeneric {name: generic_name})
        MERGE (d)-[:IS_TREATED_BY]->(g)
        RETURN COUNT(*)
        """
    )
    count = response.get_next()[0]
    print(f"Merged {count} condition-generic drug relationships into the graph")


def merge_generic_drug_brand_rel(df, conn) -> None:
    # Merge generic drug and brand drug relationships
    # First, create a dataframe with exploded drugs and processed conditions
    df_with_drugs = df.explode("drug").with_columns(
        [
            pl.col("drug").struct.field("generic_name").str.to_lowercase().alias("generic_name"),
            pl.col("drug").struct.field("brand_names").alias("brand_names"),
            pl.col("condition").str.to_lowercase().str.strip_chars().alias("condition"),
        ]
    )

    df_with_conditions = df_with_drugs.select(["generic_name", "brand_names", "condition"])

    # Finally, explode brand names and create the final dataframe
    generic_drug_brand_df = (
        df_with_conditions.explode("brand_names")
        .filter(pl.col("brand_names") != "")  # Filter out empty brand names
        .with_columns(pl.col("brand_names").str.to_lowercase().alias("brand_name"))
        .select(["generic_name", "brand_name", "condition"])
    ).unique()

    response = conn.execute(
        """
        LOAD FROM generic_drug_brand_df
        MATCH (d1:DrugGeneric {name: generic_name}), (d2:DrugBrand {name: brand_name})
        MERGE (d1)-[:HAS_BRAND]->(d2)
        RETURN COUNT(*)
        """
    )
    count = response.get_next()[0]
    print(f"Merged {count} generic drug-brand relationships into the graph")


def merge_symptom_generic_drug_rel(df, conn) -> None:
    # Merge symptom and generic drug relationships
    symptom_drug_df = (
        df.explode("side_effects")
        .explode("drug")
        .with_columns(
            [
                pl.col("side_effects").str.to_lowercase().alias("symptom"),
                pl.col("drug")
                .struct.field("generic_name")
                .str.to_lowercase()
                .alias("generic_name"),
            ]
        )
    ).unique()

    response = conn.execute(
        """
        LOAD FROM symptom_drug_df
        MATCH (d:DrugGeneric {name: generic_name}), (s:Symptom {name: symptom})
        MERGE (d)-[:CAN_CAUSE]->(s)
        RETURN COUNT(*)
        """
    )
    count = response.get_next()[0]
    print(f"Merged {count} symptom-generic drug relationships into the graph")


def main(data_path: str, conn: kuzu.Connection) -> None:
    create_node_tables(conn)
    create_rel_tables(conn)
    # Ensure that the filenames of interest are prefixed with the term "drugs"
    files = Path(data_path).glob("drugs*.json")
    for file in files:
        df = pl.read_json(file)
        df_exploded = process_condition_column(df, "condition")
        # Merge nodes
        merge_condition_nodes(df_exploded, conn)
        merge_symptom_nodes(df_exploded, conn)
        merge_generic_drug_nodes(df_exploded, conn)
        merge_brand_drug_nodes(df_exploded, conn)
        # Merge relationships
        merge_condition_generic_drug_rel(df_exploded, conn)
        merge_generic_drug_brand_rel(df_exploded, conn)
        merge_symptom_generic_drug_rel(df_exploded, conn)


if __name__ == "__main__":
    DB_NAME = "ex.kuzu"
    Path(DB_NAME).unlink(missing_ok=True)

    db = kuzu.Database(DB_NAME)
    conn = kuzu.Connection(db)

    data_path = "../data/extracted_data"
    main(data_path, conn)
