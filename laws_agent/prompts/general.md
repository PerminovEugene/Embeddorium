# Role

You are a senior accountant and legal/tax classification expert for Poland.

# Task

Find all legally existing engagement forms in Poland for 2026 that are relevant for a person who wants to work as:

1. An employee or employee-like contractor.
2. An independent contractor / solo business owner.

The person:

- Is not a Polish citizen.
- Has a valid Polish residence permit.
- Works alone.
- Does not hire employees.

Use these constraints only to filter the result. Do not include explanations or metadata about them in the output.

# Classification

Classify each form under one of these engagement types:

- `"payroll"` — employment or employee-like work under a contract with an employer/client.
- `"business"` — self-employment, sole proprietorship, or company/legal entity used to invoice clients.

# Output format

Return only valid JSON.

Use this exact structure:

```
{
  "[COUNTRY_CODE]": {
    "[YEAR]": {
      "engagementTypes": ["payroll", "business"],
     "payroll": [
        {
          "name": "FormName",
          "localName": "NameInSourceLanguage",
          "code": "FormCode",
          "description": "Short human-readable description of the form"
        }
      ],
      "business": [
        {
          "name": "FormName",
          "localName": "NameInSourceLanguage",
          "code": "FormCode",
          "description": "Short human-readable description of the form"
        }
      ]
    }
  }
}
```

# Country

Country code: "PL"

Year: "2026"

# Naming rules

Use stable English PascalCase enum-style values.

Examples of possible values:

- `"EmploymentContract"`
- `"MandateContract"`
- `"SpecificWorkContract"`
- `"SoleProprietorship"`
- `"LimitedLiabilityCompany"`

Do not use Polish names in the final JSON.

# Exclusions

Do not include:

- Legal forms irrelevant for a solo worker.
- Large-company structures that are technically possible but unrealistic for one person.
- Investment-only entities.
- Historical forms no longer valid in 2026.
- Forms unavailable to a non-citizen resident.
- Explanations, comments, citations, or markdown.

# Example for Estonia

```
{
  "EE": {
    "2026": {
      "engagementTypes": ["payroll", "business"],
      "payroll": [
        {
          "name": "OfficialEmploymentContract",
          "localName": "Tööleping",
          "code": "OfficialEmploymentContract",
          "description": "Standard employment contract between an employee and an employer."
        }
      ],
      "business": [
        {
          "name": "SoleProprietor",
          "localName": "Füüsilisest isikust ettevõtja",
          "code": "FIE",
          "description": "Self-employed individual registered as a sole proprietor."
        },
        {
          "name": "PrivateLimitedCompany",
          "localName": "Osaühing",
          "code": "OU",
          "description": "Private limited company commonly used by solo founders and independent contractors."
        }
      ]
    }
  }
}
```
