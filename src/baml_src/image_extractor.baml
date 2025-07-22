// Extract drug information and its known side effects from a table in an image
class Drug {
    generic_name string
    brand_names string[] @description("Strip the ® character at the end of the brand names")
}

class ConditionAndDrug {
    condition string
    drug Drug[]
    side_effects string[]
}

function ExtractFromPdf(img: pdf) -> ConditionAndDrug[] {
  client OpenRouterGPT41
  prompt #"
    You are an expert at extracting healthcare and pharmaceutical information.

    Extract the condition, drug names and side effects from these columns:
    - Reason for drug
    - Drug names: Generic name & (Brand name)
    - Side effects

    {{ ctx.output_format }}

    {{ _.role("user") }}
    {{ img }}
  "#
}

test ExtractFromPDF {
  functions [ExtractFromPdf]
  args {
    img {
      file "../../data/pdf/drugs_and_side_effects.pdf"
    }
  }
}
