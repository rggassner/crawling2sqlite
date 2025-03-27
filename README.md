# crawling2sqlite
Crawl the web and save urls, words, emails, images, pdfs and midis using sqlite for persistence. You an also find open directories, and categorize images checking if they are nsfw. The statistics page is able to show relationship between hosts.

You should be able to run multiple concurrent instance on the same database, but keep in mind that sqlite is not good for that scenario. It is also possible to crawl and download images simultaneously. A folder mounted in ram might help improve performance.

This is a study project I used to learn about decorators, sqlite and beautiful soup, and python in general.

The expressions have been tested against more than 10 million urls, but there are still many content types and applications that are not covered by the regular expressions. The generic expression -> function approach was intended to allow fast development of new features.

Requirements:

sudo apt install python3-pip
pip3 install fake_useragent
pip3 install selenium
pip3 install django
pip3 install bs4
pip3 install opennsfw2
pip3 install tensorflow
pip3 install random_user_agent
pip3 install django

## Viewing images

I recommend using feh to see the results in the image directory

feh -FZzD 1

## Some interesting queries

I´ve found and reported several directory traversal vulnerabilities using these queries:

- select * from urls where url like '%file=%/%' order by url;
- select * from urls where url like '%file=%' order by url;
- select * from urls where url like '%arquivo=%/%' order by url;
- select * from urls where url like '%arquivo=%' order by url;
- select * from urls where url like '%?%=%' order by url;
- select * from urls where url like '%==%' order by url;
- select * from urls where url like '%.sql%' order by url;
- select * from urls where url like '%bkp%' order by url;
- select * from urls where url like '%backup%' order by url;
- select * from urls where url like '%.tar.gz%' order by url;
- select * from urls where url like '%.tar.xz%' order by url;
- select * from urls where url like '%.tar.bz%' order by url;
- select * from urls where url like '%.zip%' order by url;
- select * from urls where url like '%upload%' order by url;
- select * from urls where url like '%register%' order by url;

## Creating the database if using mariadb

```
CREATE DATABASE crawling2mariadb;  
CREATE USER 'crawling2mariadb'@'localhost' IDENTIFIED BY 'crawling2mariadb';  
GRANT ALL PRIVILEGES ON crawling2mariadb.\* TO 'crawling2mariadb'@'localhost';  
FLUSH PRIVILEGES;  
EXIT;
```
