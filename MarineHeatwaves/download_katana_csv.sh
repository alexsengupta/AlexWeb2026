scp z3045790@katana.restech.unsw.edu.au:'/home/z3045790/SCOPUS/*.csv' .

# Move personal publications CSV to the website assets/data directory
if [ -f "scopus_alex_sen_gupta_articles_with_abstracts.csv" ]; then
    mkdir -p ../assets/data
    mv scopus_alex_sen_gupta_articles_with_abstracts.csv ../assets/data/
    echo "Moved scopus_alex_sen_gupta_articles_with_abstracts.csv → assets/data/"
fi
