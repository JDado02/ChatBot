FROM nginx:alpine

# Copia il file index.html nella directory predefinita di Nginx per servire i file statici
COPY index.html /usr/share/nginx/html/index.html

# Espone la porta 80 all'interno del container
EXPOSE 80
