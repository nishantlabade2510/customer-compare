-- Source extract for the customer comparison.
-- Keep the column list in step with config/config.yaml (columns and not_null).
-- Named bind parameters, if needed, go in the `params` block of the side config.
SELECT CustomerID,
       CustomerCode,
       CustomerName,
       DOB,
       Gender,
       Email,
       Phone,
       City,
       StateName,
       Country,
       Balance
FROM customer_source;
