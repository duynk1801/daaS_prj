# Payment Feature — Documentation

> **Feature:** Payment Processing  
> **Status:** 🔄 Planned (Phase 2)  
> **Last Updated:** 2026-06-17

---

## Overview

VNPay integration for booking payments, webhook processing, and refunds.

---

## Payment Flow

```
1. User creates booking → PENDING_PAYMENT
2. Frontend calls POST /api/v1/payments (booking_id)
3. Backend calls VNPay API → returns payment URL
4. User redirected to VNPay checkout
5. VNPay calls webhook POST /api/v1/payments/webhook/vnpay
6. Backend validates HMAC signature
7. On success → booking.status = PAID, publish PaymentSuccess event
8. On failure → booking.status = PAYMENT_FAILED
```

---

## Planned API

```
POST /api/v1/payments                    # Initiate payment for a booking
GET  /api/v1/payments/{id}              # Get payment status
POST /api/v1/payments/webhook/vnpay     # VNPay server callback (no auth)
POST /api/v1/payments/{id}/refund       # Admin: initiate refund
```

---

## Security Requirements

- VNPay webhook: validate HMAC-SHA512 signature
- Webhook endpoint: whitelist VNPay IPs
- Idempotency: webhook can fire multiple times (use event_id)
- Refund: admin role only

---

## Events Published

| Event | Routing Key | Consumers |
|-------|-------------|-----------|
| `PaymentSuccess` | `payment.success` | booking (PAID), notifications, analytics |
| `PaymentFailed` | `payment.failed` | booking (PAYMENT_FAILED), notifications |
| `RefundInitiated` | `payment.refund` | wallet, notifications |

---

## Implementation Plan

```
features/payment/
  api/
    controller.py       # initiate, webhook, refund
    schemas.py          # PaymentRequest, VNPayWebhookPayload, PaymentResponse
  domain/
    entity.py           # PaymentEntity
    status.py           # PaymentStatus: PENDING, SUCCESS, FAILED, REFUNDED
    rules.py            # validate_signature(), validate_amount()
  application/
    initiate_payment.py   # InitiatePaymentUseCase
    process_webhook.py    # ProcessWebhookUseCase (idempotent)
    refund_payment.py     # RefundPaymentUseCase
    payment_service.py    # Facade
  infrastructure/
    repository.py         # PaymentRepository
    vnpay_client.py       # VNPay API integration (httpx.AsyncClient)
    rabbitmq_publisher.py # PaymentSuccess, PaymentFailed events
```
