# Versione 2 -  Ancora più brutto

# COSA E' FANTACALCIO-PY?
 Un tool che scarica i database più recenti degli ultimi due campionati.
 Il programma provvederà poi a incrociare i dati mostrando l'andamento di un giocatore, la sua media negli ultimi due campionati la sua probabile titolarità futura (dato interessante se siamo ad inizio campionato) e due indici, uno di convenienza estrapolato dai dati e uno preso dal sito fantacalciopedia.
 Tutti questi dati verranno poi messi in un Excel per essere comparati.

# COSA INDICA LA CONVENIENZA MO?
 Per convenienza si intende il rapporto tra il valore di base in asta e il suo rendimento passato o attuale (indicato con "convenienza today")
 Ad esempio Immobile è una macchina da gol ma la sua convenienza sarà più bassa rispetto a Vlahovic, che ha non solo una media simile, ma un prezzo base inferiore.
 Allo stesso tempo, pur essendo a parità di prezzo base, un giocatore come Luis Alberto sarà più conveniente di Barak per via delle partite giocate e del rendimento.
 Ovviamente questo tool è da usare leggendo l'output dato dallo stesso programma, poichè è stato ideato non per prendere giocatori come Immobile, bensì per fare colpi a basso prezzo di giocatori ovviamente non blasonati ma comunque utili alla causa (es. un Deulofeu o uno Arnautovic presi a poco che si son dimostrati degni del ruolo di riserva).
 Può capitare di prendere giocatori come Verde che vi faranno rimpiangere di aver usato il mio algoritmo per guidarvi all'asta, ma vabbè mo lo metto come disclaimer.

 # DISCLAIMER
 - Se perdete il fanta non è colpa mia, io ci so arrivato secondo co sta roba. E l'anno dopo primo.
 - Servono pandas e bs4 per funzionare
 - Il tool utilizza i csv prodotti da fantacalciopedia, tutti i dati processati sono loro, dato che fantagazzetta ha deciso di tagliare i dataset open


Nato da un'idea di cttynul 
