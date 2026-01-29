from abc import ABC, abstractmethod

from src.application.dto.payment_dto import CreateInvoiceDTO, InvoiceResponseDTO


class PaymentGateway(ABC):
    @abstractmethod
    async def create_invoice(self, dto: CreateInvoiceDTO) -> InvoiceResponseDTO: ...

    @abstractmethod
    async def get_invoice_status(self, invoice_id: str) -> str: ...
