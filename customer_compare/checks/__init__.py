"""The individual reconciliation checks. Each module answers one question about the data.

    counts    how many rows and keys each side has
    keys      which keys are missing, extra or duplicated
    columns   whether shared records agree column by column, after transformations
    nulls     whether NOT NULL constraints hold on each side
"""
