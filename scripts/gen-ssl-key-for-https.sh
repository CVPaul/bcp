# https://blog.csdn.net/qq_41985058/article/details/136231931
# openssl genpkey -algorithm RSA -out private.key -pkeyopt rsa_keygen_bits:2048
# openssl req -new -key private.key -out cert.csr
# openssl x509 -req -days 365 -in cert.csr -signkey private.key -out certchain.pem
mkdir -p dashboard/cert && mv private.key cert.csr certchain.pem dashboard/cert