"""L06 teaching gap: this adapter incorrectly commits a partial batch."""
import csv
import io
from .identity import SYSTEM_PRINCIPAL


def submit(service, content):
    # Repair this function: validate the complete content once, then commit its job.
    for row in csv.DictReader(io.StringIO(content)):
        if not row.get('name'):
            continue
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=['sku', 'name', 'sales_price_cents'])
        writer.writeheader()
        writer.writerow(row)
        job = service.validate_csv(SYSTEM_PRINCIPAL, 'products', buffer.getvalue())
        service.commit(SYSTEM_PRINCIPAL, job['id'])
