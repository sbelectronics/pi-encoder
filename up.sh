rsync -avz --exclude "__history" --exclude "*~" --exclude "*.img" --exclude "home-pi-*" --exclude "dot*" --exclude "*.conf" --exclude "*.pyc" -e ssh . pi@198.0.0.229:/home/pi/atten

