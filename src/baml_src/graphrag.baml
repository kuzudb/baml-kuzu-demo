// --- Data models ---
class Query {
  cypher string @description("Valid Cypher query with no newlines")
}

enum Tool {
    Text2Cypher  @description("Translate the question into a valid Cypher statement")
    VectorSearchSymptoms  @description("Search for symptoms or side effects mentioned in the question")
    VectorSearchConditions  @description("Search for a condition or ailment mentioned in the question")
}

// --- Functions ---

function RAGText2Cypher(schema: string, question: string, additional_context: string | null) -> Query {
  client OpenRouterGoogleGemini25Flash
  prompt #"
    Translate the given question into a valid Cypher query that respects the given graph schema.

    <INSTRUCTIONS>
    - ALWAYS respect the relationship directions (from -> to) as provided in the <SCHEMA> section.
    - Use only the provided nodes, relationships and properties in your Cypher statement.
    - Properties can be on nodes or relationships - check the schema carefully to figure out where they are.
    - When returning results, return property values rather than the entire node or relationship.
    - ALWAYS use the WHERE clause to compare string properties, and compare them using the
      LOWER() function.
    - Pay attention to the ADDITIONAL_CONTEXT to figure out what to add in the
    WHERE clause.
    - Do not use APOC as the database does not support it.
    </INSTRUCTIONS>

    {{ _.role("user") }}
    <QUESTION>
    {{ question }}
    </QUESTION>

    <ADDITIONAL_CONTEXT>
    {{ additional_context }}
    <ADDITIONAL_CONTEXT>

    <SCHEMA>
    {{ schema }}
    </SCHEMA>

    <OUTPUT_FORMAT>
    {{ ctx.output_format }}
    </OUTPUT_FORMAT>
  "#
}

function PickTool(schema: string, query: string) -> Tool {
  client OpenRouterGPT4o
  prompt #"
    A prior attempt to write a valid Cypher query failed because an exact match with
    a property value was not found. Analyze the given query and select the most appropriate tool
    that can retrieve more useful context to answer the question.

    {{ _.role("user") }}
    <QUESTION>
    {{ query }}
    </QUESTION>

    <SCHEMA>
    {{ schema}}
    </SCHEMA>

    <OUTPUT_FORMAT>
    {{ ctx.output_format }}
    </OUTPUT_FORMAT>
  "#
}

function RAGAnswerQuestion(question: string, cypher: string, context: string) -> string {
  client OpenRouterGPT4o
  prompt #"
    You are an AI assistant for Retrieval-Augmented Generation (RAG).

    <INSTRUCTIONS>
    - Use the provided question, the generated Cypher query and the CONTEXT to answer the question.
    - If the CONTEXT is empty, state that you don't have enough information to answer the question.
    </INSTRUCTIONS>

    {{ _.role("user") }}
    <QUESTION>
    {{ question }}
    </QUESTION>
    
    <CYPHER>
    {{ cypher }}
    </CYPHER>

    <CONTEXT>
    {{ context }}
    </CONTEXT>

    {{ ctx.output_format }}

    RESPONSE:
  "#
}


// --- Test cases ---

test RAGText2Cypher1 {
  functions [RAGText2Cypher]
  args {
    schema #"
    (:Patient {patient_id: string}) -[:EXPERIENCES]-> (:Symptom {name: string})

    (:Patient {patient_id: string}) -[:IS_PRESCRIBED {date: date, dosage: string, frequency: string}]-> (:DrugGeneric {name: string})

    (:DrugGeneric {name: string}) -[:CAN_CAUSE]-> (:Symptom {name: string})

    (:DrugGeneric {name: string}) -[:HAS_BRAND]-> (:DrugBrand {name: string})

    (:Condition {name: string}) -[:IS_TREATED_BY]-> (:DrugGeneric {name: string})
    "#
    question "Which drugs are prescribed to patients with hypertension?"
    additional_context ""
  }
  @@assert({{ this|regex_match("[hH]ypertension") }})
  @@assert({{ ":Condition" in this.response }})
}

test RAGText2Cypher2 {
  functions [RAGText2Cypher]
  args {
    schema #"
    (:Patient {patient_id: string}) -[:EXPERIENCES]-> (:Symptom {name: string})

    (:Patient {patient_id: string}) -[:IS_PRESCRIBED {date: date, dosage: string, frequency: string}]-> (:DrugGeneric {name: string})

    (:DrugGeneric {name: string}) -[:CAN_CAUSE]-> (:Symptom {name: string})

    (:DrugGeneric {name: string}) -[:HAS_BRAND]-> (:DrugBrand {name: string})

    (:Condition {name: string}) -[:IS_TREATED_BY]-> (:DrugGeneric {name: string})
    "#
    question "What are the side effects of lansoprazole?"
    additional_context ""
  }
  @@assert({{ this|regex_match("[lL]ansoprazole") }})
  @@assert({{ ":Symptom" in this.response }})
}
test PickTool1 {
  functions [PickTool]
  args {
    schema #"
    (:Patient {patient_id: string}) -[:EXPERIENCES]-> (:Symptom {name: string})

    (:Patient {patient_id: string}) -[:IS_PRESCRIBED {date: date, dosage: string, frequency: string}]-> (:DrugGeneric {name: string})

    (:DrugGeneric {name: string}) -[:CAN_CAUSE]-> (:Symptom {name: string})

    (:DrugGeneric {name: string}) -[:HAS_BRAND]-> (:DrugBrand {name: string})

    (:Condition {name: string}) -[:IS_TREATED_BY]-> (:DrugGeneric {name: string})
    "#
    query "MATCH (dg:DrugGeneric)-[:CAN_CAUSE]->(s:Symptom), (dg)-[:HAS_BRAND]->(db:DrugBrand) WHERE LOWER(s.name) = LOWER('sleepiness') RETURN db.name"
  }
  @@assert( {{ this == "VectorSearchSymptoms" }})
}

test PickTool2 {
  functions [PickTool]
  args {
    schema #"
    (:Patient {patient_id: string}) -[:EXPERIENCES]-> (:Symptom {name: string})

    (:Patient {patient_id: string}) -[:IS_PRESCRIBED {date: date, dosage: string, frequency: string}]-> (:DrugGeneric {name: string})

    (:DrugGeneric {name: string}) -[:CAN_CAUSE]-> (:Symptom {name: string})

    (:DrugGeneric {name: string}) -[:HAS_BRAND]-> (:DrugBrand {name: string})

    (:Condition {name: string}) -[:IS_TREATED_BY]-> (:DrugGeneric {name: string})
    "#
    query "MATCH (c:Condition)-[:IS_TREATED_BY]->(dg:DrugGeneric) WHERE LOWER(c.name) = LOWER('high blood pressure') RETURN dg.name"
  }
  @@assert( {{ this == "VectorSearchConditions" }})
}


test RAGAnswerQuestion1 {
  functions [RAGAnswerQuestion]
  args {
    question "What drug is the patient X7F3Q prescribed, and what is the dosage and frequency?"
    cypher "MATCH (p:Patient {patient_id: 'X7F3Q'}) -[:IS_PRESCRIBED {date: date, dosage: string, frequency: string}]-> (dg:DrugGeneric) RETURN dg.name, dg.dosage, dg.frequency"
    context "ramipril, 5mg, daily"
  }
  @@assert( {{ this|regex_match("[rR]amipril") }} )
  @@assert( {{ this|regex_match("5mg") }} )
  @@assert( {{ this|regex_match("daily") }} )
}


test RAGAnswerQuestion2 {
  functions [RAGAnswerQuestion]
  args {
    question "What condition does the drug brand Digitek treat, and what are its side effects?"
    cypher "MATCH (db:DrugBrand)-[:HAS_BRAND]-(dg:DrugGeneric)-[:IS_TREATED_BY]-(c:Condition), (dg)-[:CAN_CAUSE]->(s:Symptom) WHERE LOWER(db.name) = LOWER('Digitek') RETURN c.name, s.name"
    context "dizziness, upset stomach, headache, throwing up"
  }
  @@assert( {{ this|regex_match("[dD]izziness") }} )
  @@assert( {{ this|regex_match("[uU]pset stomach") }} )
  @@assert( {{ this|regex_match("[hH]eadache") }} )
  @@assert( {{ this|regex_match("[tT]hrowing up") }} )
}
