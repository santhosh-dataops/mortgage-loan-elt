select
    loan_id,
    borrower_id,
    cast(origination_date as date)           as origination_date,
    upper(product)                           as product,
    cast(term_months as integer)             as term_months,
    upper(purpose)                           as loan_purpose,
    upper(property_state)                    as property_state,
    cast(original_balance as decimal(14, 2)) as original_balance,
    cast(interest_rate as decimal(6, 4))     as interest_rate,
    cast(credit_score as integer)            as credit_score,
    cast(ltv as decimal(5, 3))               as ltv,
    cast(dti as decimal(5, 3))               as dti,
    case
        when credit_score >= 760 then 'SUPER_PRIME'
        when credit_score >= 700 then 'PRIME'
        when credit_score >= 640 then 'NEAR_PRIME'
        else 'SUBPRIME'
    end                                      as credit_tier
from {{ source('raw', 'loan_origination') }}
