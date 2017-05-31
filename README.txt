Valeriu Predoi, 3 May 2017
--------------------------
Computational Scientist for UKESM Core Team
Department of Meteorology, University of Reading
Earley Gate, Office 1U08
READING, RG6 6BB
United Kingdom
valeriu.predoi@gmail.com
v.predoi@reading.ac.uk
Mobile number: 07847416092


Here you will find useful documentation regarding, and not exhaustively related to, various projects, including: getting data with Synda, ESMValTool, various other files, etc. This directory is under constant update from the author. Feel free to share it with anybody in the field. SVN accounts are limited  though. Cheers!

SVN requests and any other suggestions should be addressed to the author by email.


Cheers, guys!
V

[svn import]
svn import -m "first commit svn project for documentation" /home/users/valeriu/Useful_Documentation/ file:////home/users/valeriu/subversion/Useful_Documentation
[svn checkout]
svn co svn+ssh://valeriu@jasmin-sci2.ceda.ac.uk/home/users/valeriu/subversion/Useful_Documentation
[ssh settings]
vim ~/.ssh/config
add
Host jasmin
Hostname jasmin-login1.ceda.ac.uk
User valeriu [replace as appropriate]
IdentityFile ~/.ssh/id_rsa_jasmin
ForwardAgent yes

Host jasmin-sci2 jasmin-sci2.ceda.ac.uk
User valeriu [replace as appropriate]
IdentityFile ~/.ssh/id_rsa_jasmin
ForwardAgent yes
ProxyCommand ssh -Y jasmin -W %h:%p
