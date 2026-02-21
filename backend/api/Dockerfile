FROM golang:1.25-alpine AS builder
WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o /bin/backend-api ./cmd/server

FROM gcr.io/distroless/base-debian12
COPY --from=builder /bin/backend-api /bin/backend-api
EXPOSE 8080
ENTRYPOINT ["/bin/backend-api"]
