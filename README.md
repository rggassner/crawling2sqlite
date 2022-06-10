# crawling2sqlite
Crawl the web and save urls, words, emails and images using sqlite for persistence.

You should be able to run multiple concurrent instance on the same database, but keep in mind that sqlite is not good for that scenario. It is also possible to crawl and download images simultaneously.

This is a study project I used to learn about decorators, sqlite and beautiful soup.

The expressions have been tested against more than 10 million urls, but there are still many content types and applications that are not covered by the regular expressions. The generic expression -> function approach was intended to allow fast development of new features.

Requirements:

pip3 install pyOpenSSL

pip3 install django

pip3 install bs4

apt install libwebp-dev

## Viewing images

I recommend using feh to see the results in the image directory

feh -FZzD 1

## Some interesting queries

I´ve found and reported several directory traversal vulnerabilities using these queries, some were even remediated :smile:

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

Content enumeration:
- select * from urls where url like '%whatsapp-image-%' order by url;

