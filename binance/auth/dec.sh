openssl enc -d -aes-256-cbc -pbkdf2 -in $1 -out "${1%.enc}.${2}"
