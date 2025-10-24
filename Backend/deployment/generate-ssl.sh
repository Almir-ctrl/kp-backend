#!/bin/bash
# Generate self-signed SSL certificate for development

echo "🔐 Generating SSL certificate for HTTPS..."

# Create SSL directory if it doesn't exist
mkdir -p nginx/ssl

# Generate private key
openssl genrsa -out nginx/ssl/key.pem 2048

# Generate certificate signing request
openssl req -new -key nginx/ssl/key.pem -out nginx/ssl/cert.csr \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate self-signed certificate
openssl x509 -req -days 365 -in nginx/ssl/cert.csr -signkey nginx/ssl/key.pem -out nginx/ssl/cert.pem

# Clean up CSR
rm nginx/ssl/cert.csr

echo "✅ SSL certificate generated!"
echo "📄 Certificate: nginx/ssl/cert.pem"
echo "🔑 Private key: nginx/ssl/key.pem"
echo ""
echo "⚠️  This is a self-signed certificate for development only."
echo "   Browsers will show a security warning - click 'Advanced' > 'Proceed to localhost'"
echo ""
echo "🌐 Your API will be available at: https://localhost"