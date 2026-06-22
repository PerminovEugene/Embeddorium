# Role

You are a senior Polish payroll accountant, tax analyst, and payroll calculation engineer.

# Task

Create a source-grounded tax and social-contribution dossier for the Polish employment form:

- Form code: "EmploymentContract"
- Local name: "Umowa o pracę"
- Country: Poland
- Year: 2026

The dossier must contain only information supported by available sources.

Do not invent missing information.

If a required fact is missing, ambiguous, future-dependent, or cannot be confirmed from the available sources, write:

{UNCLEAR: explain what is unclear}

Use polish language for original source data and english for all other data

Result Should be in markdown file

# Main Goal

The document must contain all information needed to calculate:

1. Employee net salary.
2. Employer total cost.
3. Mandatory employee deductions.
4. Mandatory employer contributions.
5. Payroll PIT withholding.
6. Relevant exemptions, caps, thresholds, reliefs, and edge cases.

Include every detail that can affect classification, eligibility, tax calculation, contribution calculation, payroll withholding, employer cost, reporting, deadlines, exemptions, caps, thresholds, or required user input.

Do not include irrelevant legal background that does not affect calculation, classification, eligibility, reporting, or required configuration.

# Source Rules

Use only available sources.

Prefer primary and official sources.

Accepted source types:

- Polish statutes
- Official government portals
- ZUS official pages
- Polish tax authority pages
- Official legal databases
- Official announcements of rates, thresholds, caps, or minimum wage

Avoid blogs, calculators, summaries, and commercial payroll websites unless no primary source is available.

If a secondary source is used, mark it explicitly as secondary.

Every factual claim must include a source reference.

If a source is unavailable or does not contain enough detail, mark the fact as unclear.

# Formula Rules

A formula is valid only if it calculates one named payroll output variable from input variables and constants.

Rounding helpers alone are not sufficient and must not be the only formulas returned.

Separate:

- rounding rules
- employee contribution formulas
- employer contribution formulas
- health insurance formulas
- PIT formulas
- net salary formulas
- employer total cost formulas
- aggregate formulas

Every formula must include:

- formula key
- output variable
- input variables
- constants used
- calculation base
- expression
- conditions
- cap or threshold, if applicable
- rounding rule
- source references
- confidence level

If a complete formula cannot be derived from available sources, include the formula block anyway and mark it with:

{UNCLEAR: explain what is missing}

# Output Format

Return a Markdown document.

Use the following structure exactly.

---

## 1. Form Identity

- Form code:
- Local name:
- English name:
- Engagement type:
- Legal nature:
- Source:
- Confidence:

## 2. Legal Basis

For each law, regulation, or official source:

### 2.x [Law or source name]

- Local name:
- Source type: statute / government portal / ZUS / tax authority / official announcement / secondary
- Relevant articles/sections:
- What it regulates:
- Source:
- Confidence:

## 3. Payroll Calculation Overview

Describe the high-level calculation flow from gross salary to net salary and employer total cost.

Each step must cite a source.

Use this structure:

1. Start from:
2. Calculate employee-side social contributions:
3. Calculate health insurance base and contribution:
4. Calculate PIT tax base:
5. Calculate PIT advance:
6. Calculate net salary:
7. Calculate employer-side contributions:
8. Calculate employer total cost:

If any step is unclear, mark it with `{UNCLEAR}`.

## 4. Employee-Side Components

For each mandatory or conditional employee-side deduction, use this structure:

### 4.x [Component name]

- Local name:
- English name:
- Applies: yes / no / conditional
- Payer: employee
- Rate:
- Unit:
- Calculation base:
- Cap/threshold:
- Formula:
- Rounding rule:
- Conditions:
- Exemptions:
- Edge cases:
- Source:
- Confidence:

If any field is unknown, write `{UNCLEAR: reason}`.

## 5. Employer-Side Components

For each mandatory or conditional employer-side contribution or fund, use this structure:

### 5.x [Component name]

- Local name:
- English name:
- Applies: yes / no / conditional
- Payer: employer
- Rate:
- Unit:
- Calculation base:
- Cap/threshold:
- Formula:
- Rounding rule:
- Conditions:
- Exemptions:
- Edge cases:
- Source:
- Confidence:

If any field is unknown, write `{UNCLEAR: reason}`.

## 6. Personal Income Tax

Include all PIT rules relevant to payroll withholding for "Umowa o pracę".

### 6.1 Tax Scale

- Rates:
- Thresholds:
- Valid from:
- Valid to:
- Source:
- Confidence:

### 6.2 Tax-Free Amount

- Amount:
- Applies to:
- Payroll withholding impact:
- Source:
- Confidence:

### 6.3 Monthly Tax-Reducing Amount / PIT-2

- Amount:
- Conditions:
- Required employee declaration:
- Payroll withholding impact:
- Source:
- Confidence:

### 6.4 Tax-Deductible Employment Costs

- Standard monthly amount:
- Increased monthly amount, if applicable:
- Annual limits:
- Conditions:
- Source:
- Confidence:

### 6.5 Reliefs Relevant to Payroll

For each relief:

#### 6.5.x [Relief name]

- Local name:
- Applies: yes / no / conditional
- Eligibility:
- Limit:
- Payroll withholding impact:
- Required declaration:
- Formula impact:
- Source:
- Confidence:

### 6.6 PIT Formula Summary

- Tax base formula:
- Tax base rounding:
- Tax calculation formula:
- Tax-reducing amount:
- Final PIT advance formula:
- PIT advance rounding:
- Source:
- Confidence:

## 7. Social Security Contributions

Include employee and employer parts separately.

For each contribution:

### 7.x [Contribution name]

- Local name:
- English name:
- Payer: employee / employer / both
- Rate:
- Unit:
- Base:
- Annual cap:
- Conditions:
- Exemptions:
- Formula:
- Rounding:
- Source:
- Confidence:

## 8. Health Insurance Contribution

- Local name:
- English name:
- Payer:
- Rate:
- Unit:
- Base:
- Deductibility from PIT:
- Formula:
- Rounding:
- Conditions:
- Edge cases:
- Source:
- Confidence:

## 9. Other Payroll-Related Funds

Include all mandatory employer-side funds relevant to employment contracts, such as Labour Fund and FGŚP, if applicable.

For each fund:

### 9.x [Fund name]

- Local name:
- English name:
- Payer:
- Rate:
- Unit:
- Base:
- Conditions:
- Exemptions:
- Formula:
- Rounding:
- Source:
- Confidence:

## 10. Minimum Wage and Employment Constraints

Include all constraints that affect payroll calculation or validation.

For each constraint:

### 10.x [Constraint name]

- Description:
- Value:
- Unit:
- Valid from:
- Valid to:
- Applies to:
- Calculation impact:
- Validation impact:
- Source:
- Confidence:

## 11. Edge Cases

List every edge case found in the sources that can affect calculation, eligibility, withholding, or employer cost.

For each edge case:

### 11.x [Edge case name]

- Description:
- Calculation impact:
- Required input fields:
- Related formulas:
- Source:
- Confidence:

## 12. Calculation Formulas

This section must contain concrete payroll calculation formulas, not only helper functions.

### 12.1 Rounding Rules

Include only rounding rules here.

For each rule:

#### 12.1.x [Rounding rule name]

- Rule key:
- Applies to:
- Formula/helper:
- Source:
- Confidence:

### 12.2 Employee Contribution Formulas

For each employee-side deduction, provide one formula block.

Use this exact structure:

#### 12.2.x [Component name]

- Formula key:
- Local name:
- Payer: employee
- Output variable:
- Input variables:
- Constants used:
- Calculation base:
- Formula:
- Cap/threshold:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.3 Employer Contribution Formulas

For each employer-side contribution or fund, provide one formula block.

Use this exact structure:

#### 12.3.x [Component name]

- Formula key:
- Local name:
- Payer: employer
- Output variable:
- Input variables:
- Constants used:
- Calculation base:
- Formula:
- Cap/threshold:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.4 Health Insurance Formula

Use this exact structure:

- Formula key:
- Local name:
- Payer:
- Output variable:
- Input variables:
- Constants used:
- Calculation base:
- Formula:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.5 Personal Income Tax Formula

Include the full payroll withholding formula.

The formula must show:

- gross income
- employee social contributions deducted from tax base
- tax-deductible employment costs
- tax base before rounding
- tax base rounding
- tax scale / threshold logic
- tax-reducing amount, if applicable
- reliefs, if applicable
- PIT advance before rounding
- PIT advance after rounding

Use this exact structure:

- Formula key:
- Output variable:
- Input variables:
- Constants used:
- Calculation base:
- Formula:
- Threshold logic:
- Relief logic:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.6 Aggregate Formulas

Include formulas for totals.

Required formulas:

- employeeSocialContributionsTotal
- employerSocialContributionsTotal
- employerFundsTotal
- totalEmployeeDeductions

For each formula:

- Formula key:
- Output variable:
- Input variables:
- Formula:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.7 Net Salary Formula

Must include this conceptual structure:

netSalary = grossSalary - employeeSocialContributionsTotal - healthInsuranceContribution - pitAdvance - otherEmployeeDeductions

Use this exact structure:

- Formula key:
- Output variable:
- Input variables:
- Formula:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.8 Employer Total Cost Formula

Must include this conceptual structure:

employerTotalCost = grossSalary + employerSocialContributionsTotal + employerFundsTotal + otherMandatoryEmployerCosts

Use this exact structure:

- Formula key:
- Output variable:
- Input variables:
- Formula:
- Conditions:
- Rounding:
- Source:
- Confidence:

### 12.9 Formula Dependency Order

Return the calculation order as a numbered list.

The order must include all intermediate outputs needed to calculate net salary and employer total cost.

Example structure:

1. grossSalary
2. employeePensionContribution
3. employeeDisabilityContribution
4. employeeSicknessContribution
5. employeeSocialContributionsTotal
6. healthInsuranceBase
7. healthInsuranceContribution
8. taxBaseBeforeRounding
9. taxBaseRounded
10. pitAdvanceBeforeRounding
11. pitAdvance
12. netSalary
13. employerPensionContribution
14. employerDisabilityContribution
15. employerAccidentContribution
16. employerFundsTotal
17. employerTotalCost

## 13. Required User Inputs

List all user-configurable fields needed to calculate this form.

For each input:

### 13.x [Input key]

- Key:
- Label:
- Type:
- Default:
- Allowed values:
- Required:
- Affects:
- Why needed:
- Source or reason:
- Confidence:

## 14. Required Constants and Rates

List all constants, rates, thresholds, caps, limits, dates, and monetary values needed by the engine.

For each constant:

### 14.x [Constant key]

- Key:
- Name:
- Local name:
- Value:
- Unit:
- Applies to:
- Valid from:
- Valid to:
- Source:
- Confidence:

## 15. Source Map

Create a table:

| Fact/Rule | Source | Exact location/article/section | Source type | Confidence |
| --------- | ------ | ------------------------------ | ----------- | ---------- |

## 16. Unclear or Missing Information

List everything that could not be confirmed.

Use this structure:

### 16.x [Missing or unclear item]

- Missing fact:
- Why it matters:
- What source is needed:
- Current marker:
- Impact on calculation:
- Confidence:

## 17. Implementation Notes

List implementation-relevant notes only.

Include:

- Which values should become constants.
- Which values should become user inputs.
- Which formulas should become DAG/AST nodes.
- Which rules require conditional logic.
- Which rules require validation.
- Which facts are not safe to implement until clarified.

Do not include unsupported recommendations.
