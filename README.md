# crawling2sqlite
Crawl the web and save urls, words, emails and images using sqlite for persistence.

You should be able to run multiple concurrent instance on the same database, but keep in mind that sqlite is not good for that scenario. It is also possible to crawl and download images simultaneously.

This is a study project I used to learn about decorators, sqlite and beautiful soup.

The expressions have been tested against more than 10 million urls, but there are still many content types and applications that are not covered by the regular expressions. The generic expression -> function approach was intended to allow fast development of new features.

Requirements:

pip3 install pyOpenSSL
pip3 install django
pip3 install bs4
