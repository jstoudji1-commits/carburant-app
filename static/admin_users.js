/* Fiche reservee a l'administration. Toutes les donnees sont inserees comme texte. */
let ficheAdminCourante = null;
let sequenceFicheAdmin = 0;
function champFiche(id) { return document.getElementById('fiche-' + id); }
function tableauFiche(titre, lignes, colonnes) {
    const section = document.createElement('section');
    const h = document.createElement('h3'); h.textContent = titre; section.append(h);
    if (!lignes.length) { const p=document.createElement('p'); p.textContent='Aucune donnée enregistrée.';section.append(p); return section; }
    const wrap=document.createElement('div');wrap.className='table-wrap';
    const table=document.createElement('table');const head=table.createTHead().insertRow();
    colonnes.forEach(([key,label])=>{const th=document.createElement('th');th.textContent=label;head.append(th);});
    const body=table.createTBody();
    lignes.forEach(ligne=>{const tr=body.insertRow();colonnes.forEach(([key])=>{
        const cell=tr.insertCell();let value=ligne[key];
        cell.textContent=value == null ? '—' : typeof value === 'object' ? JSON.stringify(value) : typeof value === 'boolean' ? (value?'Oui':'Non') : String(value);
    });});wrap.append(table);section.append(wrap);return section;
}
function remplirFicheAdmin(fiche) {
    ficheAdminCourante=fiche;
    champFiche('titre').textContent=fiche.email;
    ['nom','ville','telephone'].forEach(k=>champFiche(k).value=fiche.profil[k] || '');
    champFiche('plan').value=fiche.plan;
    champFiche('verifie').checked=fiche.email_verified;
    champFiche('bonus').value=fiche.parrainage.bonus_until || '';
    champFiche('note').value=fiche.note || '';
    champFiche('motif').value='';
    champFiche('resume').textContent='Créé le '+texteDate(fiche.created_at)
        +' · Premium effectif : '+(fiche.premium_actif?'oui':'non')
        +' · Économies enregistrées : '+Number(fiche.statistiques.economies_total||0).toLocaleString('fr-FR',{style:'currency',currency:'EUR'})
        +' · '+fiche.historique.length+' opération(s) · Plateforme : '+(fiche.plateforme_derniere_connexion||fiche.plateforme_creation||'non renseignée');
    const details=champFiche('details');details.replaceChildren();
    const referral=document.createElement('p');referral.textContent='Code de parrainage : '+(fiche.parrainage.code||'non attribué')
        +' · Parrain : '+(fiche.parrain||fiche.parrainage.parrain_email||'aucun')
        +' · Mois de bonus cumulés : '+(fiche.parrainage.bonus_mois_total||0);details.append(referral);
    details.append(tableauFiche('Comptes filleuls',fiche.filleuls_comptes,[['email','E-mail'],['plan','Formule'],['email_verified','E-mail validé'],['bonus_attribue','Bonus attribué'],['created_at','Inscription']]));
    details.append(tableauFiche('Historique des parrainages validés (adresses parfois masquées)',fiche.parrainage.filleuls||[],[['email','Filleul'],['statut','Statut'],['bonus_mois','Mois offerts'],['validated_at','Validation']]));
    details.append(tableauFiche('Parrainages en attente',fiche.parrainage.filleuls_en_attente||[],[['email','Filleul'],['statut','Statut'],['created_at','Inscription']]));
    details.append(tableauFiche('Historique des économies synchronisées',fiche.historique,[['date','Date'],['economie','Économie (€)'],['station','Station'],['vehicule','Véhicule'],['carburant','Carburant']]));
    details.append(tableauFiche('Véhicules',fiche.vehicules,[['nom','Nom'],['profil','Énergie'],['reservoir','Réservoir'],['conso','Consommation'],['jauge','Jauge (%)']]));
    details.append(tableauFiche('Favoris',fiche.favoris.map(v=>typeof v==='object'?v:{id:v}),[['id','Identifiant'],['enseigne','Enseigne'],['ville','Ville']]));
    details.append(tableauFiche('Abonnement Apple (lecture seule)',Object.keys(fiche.abonnement_apple).length?[fiche.abonnement_apple]:[],[['product_id','Produit'],['expiration_date','Expiration'],['status','Statut'],['environment','Environnement']]));
    details.append(tableauFiche('Journal des modifications administrateur',fiche.journal.slice().reverse(),[['date','Date'],['acteur','Auteur'],['motif','Motif'],['changements','Modifications']]));
}
async function ouvrirFicheUtilisateur(email) {
    const sequence=++sequenceFicheAdmin;
    const dialog=champFiche('dialog');if(!dialog.open)dialog.showModal();
    champFiche('titre').textContent=email;champFiche('status').textContent='Chargement…';
    champFiche('form').hidden=true;
    try {
        const fiche=await requeteAdmin('/api/admin/utilisateur?email='+encodeURIComponent(email));
        if(sequence!==sequenceFicheAdmin)return;
        remplirFicheAdmin(fiche);champFiche('form').hidden=false;champFiche('status').textContent='';
    } catch(error) { if(sequence===sequenceFicheAdmin)champFiche('status').textContent=error.message; }
}
async function enregistrerFicheUtilisateur(event) {
    event.preventDefault();if(!ficheAdminCourante)return;
    const bouton=champFiche('enregistrer');bouton.disabled=true;
    const sequence=sequenceFicheAdmin;
    try {
        const fiche=await requeteAdmin('/api/admin/utilisateur',{method:'POST',body:JSON.stringify({
            email:ficheAdminCourante.email,version:ficheAdminCourante.version,
            nom:champFiche('nom').value,ville:champFiche('ville').value,telephone:champFiche('telephone').value,
            plan:champFiche('plan').value,email_verified:champFiche('verifie').checked,
            bonus_until:champFiche('bonus').value,note:champFiche('note').value,motif:champFiche('motif').value
        })});
        if(sequence===sequenceFicheAdmin){remplirFicheAdmin(fiche);champFiche('status').textContent='Modifications enregistrées.';}
        const data=await requeteAdmin('/api/admin/donnees');afficherComptes(data.comptes||[]);afficherStats(data.stats||{});
    } catch(error) { if(sequence===sequenceFicheAdmin)champFiche('status').textContent=error.message; }
    finally {bouton.disabled=false;}
}
document.getElementById('comptes-wrap').addEventListener('click',event=>{
    const button=event.target.closest('[data-compte-email]');
    if(button && button.dataset.plan)changerPlan(button.dataset.compteEmail,button.dataset.plan);
    else if(button)ouvrirFicheUtilisateur(button.dataset.compteEmail);
});

function filtrerComptesAdmin(texte) {
    document.querySelectorAll('#comptes-wrap tbody tr').forEach(row=>{
        const button=row.querySelector('[data-compte-email]');
        row.hidden=Boolean(button && !button.dataset.compteEmail.toLowerCase().includes(texte.trim().toLowerCase()));
    });
}
