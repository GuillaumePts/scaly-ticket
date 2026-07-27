class ModalManager {
    constructor() {
        this.overlay = document.getElementById('custom-modal');
        this.titleEl = document.getElementById('modal-title');
        this.messageEl = document.getElementById('modal-message');
        this.iconEl = document.getElementById('modal-icon');
        this.confirmBtn = document.getElementById('modal-confirm');
        this.cancelBtn = document.getElementById('modal-cancel');
    }

    show(title, message, iconName = 'info', iconClass = 'icon-info', showCancel = false) {
        return new Promise((resolve) => {
            this.titleEl.textContent = title;
            this.messageEl.textContent = message;
            this.iconEl.innerHTML = `<i data-lucide="${iconName}" class="${iconClass}"></i>`;
            lucide.createIcons(); // Refresh icons for modal
            
            this.overlay.style.display = 'flex';
            this.cancelBtn.style.display = showCancel ? 'flex' : 'none';

            const onConfirm = () => {
                this.close();
                resolve(true);
            };

            const onCancel = () => {
                this.close();
                resolve(false);
            };

            this.confirmBtn.onclick = onConfirm;
            this.cancelBtn.onclick = onCancel;
        });
    }

    alert(title, message, iconName = 'info', iconClass = 'icon-info') {
        return this.show(title, message, iconName, iconClass, false);
    }

    error(title, message) {
        return this.show(title, message, 'alert-circle', 'icon-error', false);
    }

    confirm(title, message, iconName = 'help-circle', iconClass = 'icon-info') {
        return this.show(title, message, iconName, iconClass, true);
    }

    close() {
        this.overlay.style.display = 'none';
    }
}

const Modal = new ModalManager();

// Initialisation des icônes Lucide
lucide.createIcons();

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const printerSelect = document.getElementById('printer');
const printerStatus = document.getElementById('printer-status');
const logs = document.getElementById('logs');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');

const sectorBtns = document.querySelectorAll('.sector-btn');
const formatBtns = document.querySelectorAll('.format-btn');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

const uploadSection = document.getElementById('upload-section');
const parfumSection = document.getElementById('parfum-section');

const editSection = document.getElementById('edit-section');
const productsTableBody = document.querySelector('#products-table tbody');
const selectAllCheckbox = document.getElementById('select-all');
const orderClient = document.getElementById('order-client');
const orderId = document.getElementById('order-id');
const printBtn = document.getElementById('print-btn');
const printAllBtn = document.getElementById('print-all-btn');
const cancelBtn = document.getElementById('cancel-btn');

let currentData = [];
let pollingInterval = null;
let isPrinterReady = false;
let isPrinting = false;
let currentFormat = '3up'; // Par défaut

// ETAPE 1 : Gestion des secteurs
sectorBtns.forEach(btn => {
    btn.onclick = () => {
        const sector = btn.dataset.sector;
        activateSector(sector, true);
    };
});

function activateSector(sector, saveState = true) {
    const btn = Array.from(sectorBtns).find(b => b.dataset.sector === sector);
    if (!btn) return;

    sectorBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    
    fileInput.value = '';
    currentData = [];
    editSection.style.display = 'none';
    progressContainer.style.display = 'none';
    
    filterPrinters(sector);
    
    // Afficher l'étape 2 (Imprimante) et 3 (Format)
    step2.style.display = 'block';
    step3.style.display = 'block';
    updateFormatVisibility();
    
    addLog(`Secteur sélectionné : ${btn.textContent.trim()}`);
    
    if (saveState) {
        history.pushState({ sector: sector }, "", "?sector=" + sector);
    }
    
    // Scroll doucement vers l'étape 2
    step2.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function resetToHome(saveState = true) {
    sectorBtns.forEach(b => b.classList.remove('active'));
    const allHubBtns = document.querySelectorAll('.hub-sector-btn');
    if(allHubBtns) allHubBtns.forEach(b => b.classList.remove('active'));
    
    const hubTools = document.getElementById('hub-tools-choice');
    if(hubTools) hubTools.style.display = 'none';

    step2.style.display = 'none';
    step3.style.display = 'none';
    uploadSection.style.display = 'none';
    parfumSection.style.display = 'none';
    editSection.style.display = 'none';
    progressContainer.style.display = 'none';
    
    const techSection = document.getElementById('technician-section');
    if (techSection) techSection.style.display = 'none';
    
    if (saveState) {
        history.pushState(null, "", window.location.pathname);
    }
}

// Gestion popstate (Bouton Précédent/Suivant)
window.addEventListener('popstate', (e) => {
    if (e.state && e.state.sector) {
        activateSector(e.state.sector, false);
    } else {
        const params = new URLSearchParams(window.location.search);
        const urlSector = params.get('sector');
        if (urlSector) {
            activateSector(urlSector, false);
        } else {
            resetToHome(false);
        }
    }
});

const hubSectorChoice = document.getElementById('hub-sector-choice');
const hubToolsChoice = document.getElementById('hub-tools-choice');
const wizardSection = document.getElementById('wizard-section');
const logContainer = document.getElementById('log-container');

// Mode Hub : Choix du secteur
const hubSectorBtns = document.querySelectorAll('.hub-sector-btn:not(#tech-mode-btn)');
const toolCards = document.querySelectorAll('.tool-card');

hubSectorBtns.forEach(btn => {
    btn.onclick = () => {
        const sector = btn.dataset.sector;
        hubSectorBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        // Affiche la grille des outils
        hubToolsChoice.style.display = 'block';
        
        // Filtre les cartes d'outils et met à jour leurs liens
        toolCards.forEach(card => {
            const allowedSectors = card.dataset.sectors.split(' ');
            if (allowedSectors.includes(sector)) {
                card.style.display = 'block';
                card.href = `?tool=${card.dataset.tool}&sector=${sector}`;
            } else {
                card.style.display = 'none';
            }
        });
    };
});

const techModeBtn = document.getElementById('tech-mode-btn');
if (techModeBtn) {
    techModeBtn.addEventListener('click', () => {
        hubToolsChoice.style.display = 'none';
        wizardSection.style.display = 'block';
        
        document.getElementById('step1').style.display = 'none';
        step2.style.display = 'none';
        step3.style.display = 'none';
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'none';
        
        const techSection = document.getElementById('technician-section');
        if (techSection) techSection.style.display = 'block';
        
        localPrinters = [...printersData];
        renderManageTable();
        
        hubSectorBtns.forEach(b => b.classList.remove('active'));
        techModeBtn.classList.add('active');
        
        history.pushState({ sector: 'expert' }, "", "?tool=expert");
    });
}

// Au chargement initial (Restore state from URL)
window.addEventListener('DOMContentLoaded', async () => {
    // Vérification de la licence en premier lieu
    try {
        const res = await fetch('/api/licence');
        const data = await res.json();
        if (!data.valid) {
            await Modal.error("Licence Invalide ou Expirée", data.error + "\n\nVotre Identifiant Machine : " + data.machine_id);
            document.body.style.pointerEvents = 'none';
            document.body.style.opacity = '0.4';
            return; // Bloque le reste de l'initialisation
        }
    } catch(e) {
        console.error("Erreur vérification licence", e);
    }

    const params = new URLSearchParams(window.location.search);
    const tool = params.get('tool');
    const sector = params.get('sector');

    if (tool && sector) {
        // Page dédiée lancée depuis le hub
        activateDedicatedTool(tool, sector);
    } else if (sector && !tool) {
        // Mode Expert (Ancien mode) avec secteur sauvegardé
        hubSectorChoice.style.display = 'none';
        hubToolsChoice.style.display = 'none';
        wizardSection.style.display = 'block';
        history.replaceState({ sector: sector }, "", "?sector=" + sector);
        setTimeout(() => activateSector(sector, false), 100); 
    } else {
        // Mode Hub (Accueil complet)
        hubSectorChoice.style.display = 'block';
        hubToolsChoice.style.display = 'none';
        wizardSection.style.display = 'none';
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'none';
        logContainer.style.display = 'none'; // Pas de log sur le hub
    }
});

function activateDedicatedTool(tool, sector) {
    hubSectorChoice.style.display = 'none';
    hubToolsChoice.style.display = 'none';
    
    // Au lieu de cacher tout le wizard, on l'affiche mais on cache ses enfants inutiles
    wizardSection.style.display = 'block';
    document.getElementById('step1').style.display = 'none';
    document.getElementById('step3').style.display = 'none';
    document.getElementById('step2').style.display = 'none';

    // Reset Step 2 DOM defaults in case it was modified by Ligne 1
    const printerSelectBox = document.querySelector('.printer-selection-box > div');
    if (printerSelectBox) printerSelectBox.style.display = 'flex';
    const step2H2 = document.getElementById('step2').querySelector('h2');
    if (step2H2) step2H2.textContent = "Sur quelle machine voulez-vous imprimer ?";
    const step2Help = document.getElementById('step2').querySelector('.help-text');
    if (step2Help) step2Help.innerHTML = "<i data-lucide='info'></i> Choisissez l'imprimante qui va sortir vos étiquettes parmi celles disponibles dans votre atelier.";
    const ligne1Details = document.getElementById('ligne1-printer-details');
    if (ligne1Details) ligne1Details.style.display = 'none';

    logContainer.style.display = 'block';

    const helpBtn = document.getElementById('help-modal-btn');
    if (helpBtn) helpBtn.style.display = 'none';

    // Configurer l'imprimante (en fond) pour le secteur
    filterPrinters(sector);

    if (tool === 'toshiba_3up' || tool === 'toshiba_4up') {
        if (helpBtn) helpBtn.style.display = 'block'; // Affiche l'aide Toshiba
        
        Array.from(printerSelect.options).forEach(opt => {
            if (opt.dataset.language !== 'TPCL') opt.remove();
        });
        
        // Sélectionne l'imprimante TPCL parmi celles du secteur
        const toshibas = Array.from(printerSelect.options);
        if (toshibas.length > 0) {
            printerSelect.value = toshibas[0].value;
            printerSelect.dispatchEvent(new Event('change'));
            updatePrinterStatus();
            
            // S'il y a plus d'une imprimante Toshiba, on affiche le sélecteur
            if (toshibas.length > 1) {
                document.getElementById('step2').style.display = 'block';
                const stepNum = document.getElementById('step2').querySelector('.step-number');
                if(stepNum) stepNum.style.display = 'none';
            }
        } else {
            Modal.error("Imprimante introuvable", "Aucune imprimante Toshiba n'est configurée pour ce secteur !");
        }
    } else if (tool.startsWith('zebra')) {
        Array.from(printerSelect.options).forEach(opt => {
            if (opt.dataset.language !== 'ZPL') opt.remove();
        });

        // Sélectionne l'imprimante ZPL parmi celles du secteur
        const zebras = Array.from(printerSelect.options);
        if (zebras.length > 0) {
            printerSelect.value = zebras[0].value;
            printerSelect.dispatchEvent(new Event('change'));
            updatePrinterStatus();
            
            // S'il y a plus d'une imprimante Zebra, on affiche le sélecteur
            if (zebras.length > 1) {
                document.getElementById('step2').style.display = 'block';
                const stepNum = document.getElementById('step2').querySelector('.step-number');
                if(stepNum) stepNum.style.display = 'none';

                if (tool === 'zebra') {
                    // Customisation Ligne 1
                    document.querySelector('.printer-selection-box > div').style.display = 'none';
                    document.getElementById('step2').querySelector('h2').textContent = "Imprimantes Ligne 1 (Automatique)";
                    document.getElementById('step2').querySelector('.help-text').innerHTML = "<i data-lucide='check-circle'></i> L'impression sera répartie automatiquement sur ces deux machines :";
                    
                    let staticBlock = document.getElementById('ligne1-printer-details');
                    if (!staticBlock) {
                        staticBlock = document.createElement('div');
                        staticBlock.id = 'ligne1-printer-details';
                        staticBlock.className = 'hub-grid';
                        staticBlock.style.marginTop = '15px';
                        document.querySelector('.printer-selection-box').appendChild(staticBlock);
                    }
                    staticBlock.style.display = 'grid';
                    
                    const cartonPrinter = zebras.find(o => o.text.startsWith("Zebra Prépa commande") && !o.text.includes("x2"));
                    const potsPrinter = zebras.find(o => o.text.includes("x2"));
                    
                    staticBlock.innerHTML = `
                        <div class="hub-card tool-card" style="display:flex; flex-direction:column; align-items:center; cursor:default; pointer-events:none;">
                            <i data-lucide="box" class="hub-icon text-orange"></i>
                            <h3 style="margin: 10px 0 5px 0;">${cartonPrinter ? cartonPrinter.text : 'Zebra (Cartons)'}</h3>
                            <p style="margin: 0; font-size: 14px; opacity: 0.8;">${cartonPrinter ? cartonPrinter.value : 'IP introuvable'}</p>
                        </div>
                        <div class="hub-card tool-card" style="display:flex; flex-direction:column; align-items:center; cursor:default; pointer-events:none;">
                            <i data-lucide="tags" class="hub-icon text-green"></i>
                            <h3 style="margin: 10px 0 5px 0;">${potsPrinter ? potsPrinter.text : 'Zebra (Pots x2)'}</h3>
                            <p style="margin: 0; font-size: 14px; opacity: 0.8;">${potsPrinter ? potsPrinter.value : 'IP introuvable'}</p>
                        </div>
                    `;
                    lucide.createIcons();
                }
            }
        } else {
            Modal.error("Imprimante introuvable", "Aucune imprimante Zebra n'est configurée pour ce secteur !");
        }
    }

    if (tool === 'toshiba_3up') {
        currentFormat = '3up';
        uploadSection.style.display = 'block';
        parfumSection.style.display = 'none';
        const stepNum = uploadSection.querySelector('.step-number');
        if (stepNum) stepNum.style.display = 'none';
        uploadSection.querySelector('h2').textContent = "Sélection du fichier de commandes";
    } else if (tool === 'toshiba_4up') {
        currentFormat = '4up';
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'block';
        const stepNum = parfumSection.querySelector('.step-number');
        if (stepNum) stepNum.style.display = 'none';
        parfumSection.querySelector('h2').textContent = "Configuration des étiquettes";
    } else if (tool.startsWith('zebra')) {
        currentFormat = '1up'; // Zebra 300 1-up
        uploadSection.style.display = 'block';
        parfumSection.style.display = 'none';
        const stepNum = uploadSection.querySelector('.step-number');
        if (stepNum) stepNum.style.display = 'none';
        uploadSection.querySelector('h2').textContent = "Commandes (Zebra 1-up)";
    }
}

// ETAPE 3 : Gestion du format d'impression
formatBtns.forEach(btn => {
    btn.onclick = () => {
        formatBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFormat = btn.dataset.format;
        updateFormatVisibility();
    }
});

function updateFormatVisibility() {
    if (currentFormat === '3up') {
        uploadSection.style.display = 'block';
        parfumSection.style.display = 'none';
    } else {
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'block';
    }
}

// ETAPE 4 (Parfums) : Chargement des parfums 4-up
const parfumSelect = document.getElementById('parfum-select');
const parfumPreviewImg = document.getElementById('parfum-preview-img');
const parfumPreviewEmpty = document.getElementById('parfum-preview-empty');

parfumSelect.addEventListener('change', () => {
    if (parfumSelect.value) {
        parfumPreviewImg.src = `/api/preview-4up/${parfumSelect.value}?t=${new Date().getTime()}`;
        parfumPreviewImg.style.display = 'inline-block';
        parfumPreviewEmpty.style.display = 'none';
    } else {
        parfumPreviewImg.style.display = 'none';
        parfumPreviewEmpty.style.display = 'block';
    }
});

fetch('/api/parfums-4up')
    .then(res => res.json())
    .then(parfums => {
        parfumSelect.innerHTML = '';
        parfums.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.nom}`;
            opt.dataset.ean = p.ean13;
            opt.dataset.nomImpression = p.nom_impression || p.nom;
            parfumSelect.appendChild(opt);
        });
        if (parfums.length > 0) {
            parfumSelect.dispatchEvent(new Event('change'));
        }
    })
    .catch(err => {
        parfumSelect.innerHTML = '<option value="">Erreur de chargement</option>';
        console.error(err);
    });

// Gestion du formulaire "Nouveau/Edition Parfum"
const toggleAddParfumBtn = document.getElementById('toggle-add-parfum-btn');
const editParfumBtn = document.getElementById('edit-parfum-btn');
const deleteParfumBtn = document.getElementById('delete-parfum-btn');
const addParfumForm = document.getElementById('add-parfum-form');
const parfumFormTitle = document.getElementById('parfum-form-title');
const editParfumId = document.getElementById('edit-parfum-id');
const newParfumNom = document.getElementById('new-parfum-nom');
const newParfumNomImpression = document.getElementById('new-parfum-nom-impression');
const newParfumEan = document.getElementById('new-parfum-ean');
const previewNewParfumBtn = document.getElementById('preview-new-parfum-btn');
const saveNewParfumBtn = document.getElementById('save-new-parfum-btn');
const cancelParfumBtn = document.getElementById('cancel-parfum-btn');

function showParfumForm(isEdit = false) {
    addParfumForm.style.display = 'block';
    if (isEdit) {
        parfumFormTitle.innerHTML = '<i data-lucide="edit"></i> Modifier le parfum';
        const opt = parfumSelect.options[parfumSelect.selectedIndex];
        newParfumNom.value = opt.text;
        newParfumNomImpression.value = opt.dataset.nomImpression || opt.text;
        newParfumEan.value = opt.dataset.ean || "";
        editParfumId.value = opt.value;
    } else {
        parfumFormTitle.innerHTML = '<i data-lucide="tag"></i> Créer un nouveau parfum';
        newParfumNom.value = '';
        newParfumNomImpression.value = '';
        newParfumEan.value = '';
        editParfumId.value = '';
    }
    toggleAddParfumBtn.style.display = 'none';
    editParfumBtn.style.display = 'none';
    deleteParfumBtn.style.display = 'none';
    lucide.createIcons();
}

function hideParfumForm() {
    addParfumForm.style.display = 'none';
    toggleAddParfumBtn.style.display = 'inline-flex';
    editParfumBtn.style.display = 'inline-flex';
    deleteParfumBtn.style.display = 'inline-flex';
}

toggleAddParfumBtn.onclick = () => showParfumForm(false);
editParfumBtn.onclick = () => {
    if (!parfumSelect.value) return;
    showParfumForm(true);
};
cancelParfumBtn.onclick = hideParfumForm;

deleteParfumBtn.onclick = async () => {
    const parfumId = parfumSelect.value;
    if (!parfumId) return;
    const opt = parfumSelect.options[parfumSelect.selectedIndex];
    
    const ok = await Modal.confirm("Supprimer le parfum", `Voulez-vous vraiment supprimer le parfum "${opt.text}" ?`, 'trash-2', 'icon-warning');
    if (!ok) return;

    try {
        const response = await fetch(`/api/parfums-4up/${parfumId}`, { method: 'DELETE' });
        if (response.ok) {
            opt.remove();
            if (parfumSelect.options.length > 0) {
                parfumSelect.value = parfumSelect.options[0].value;
                parfumSelect.dispatchEvent(new Event('change'));
            } else {
                parfumPreviewImg.style.display = 'none';
                parfumPreviewEmpty.style.display = 'block';
            }
        } else {
            const result = await response.json();
            Modal.error("Erreur", result.detail);
        }
    } catch (e) {
        Modal.error("Erreur réseau", e.message);
    }
};

previewNewParfumBtn.onclick = () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    const nom_impression = newParfumNomImpression.value.trim();
    
    if (!nom || !ean) {
        Modal.error("Informations manquantes", "Veuillez taper le nom et le code barre EAN-13.");
        return;
    }
    
    parfumPreviewImg.src = `/api/preview-4up-live?nom=${encodeURIComponent(nom)}&ean13=${encodeURIComponent(ean)}&nom_impression=${encodeURIComponent(nom_impression)}&t=${new Date().getTime()}`;
    parfumPreviewImg.style.display = 'inline-block';
    parfumPreviewEmpty.style.display = 'none';
};

saveNewParfumBtn.onclick = async () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    const nom_impression = newParfumNomImpression.value.trim();
    const isEdit = editParfumId.value !== '';
    const parfumId = editParfumId.value;
    
    if (!nom || !ean) {
        Modal.error("Informations manquantes", "Veuillez taper le nom et le code barre EAN-13.");
        return;
    }
    
    try {
        const url = isEdit ? `/api/parfums-4up/${parfumId}` : '/api/parfums-4up';
        const method = isEdit ? 'PUT' : 'POST';
        
        const response = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom, ean13: ean, nom_impression })
        });
        
        const result = await response.json();
        if (response.ok) {
            Modal.alert("Enregistré !", `Le parfum a été ${isEdit ? 'modifié' : 'créé'} avec succès.`, 'check-circle', 'icon-success');
            
            if (isEdit) {
                const opt = parfumSelect.options[parfumSelect.selectedIndex];
                opt.text = result.parfum.nom;
                opt.dataset.ean = result.parfum.ean13;
                opt.dataset.nomImpression = result.parfum.nom_impression || result.parfum.nom;
            } else {
                const opt = document.createElement('option');
                opt.value = result.parfum.id;
                opt.textContent = result.parfum.nom;
                opt.dataset.ean = result.parfum.ean13;
                opt.dataset.nomImpression = result.parfum.nom_impression || result.parfum.nom;
                parfumSelect.appendChild(opt);
                parfumSelect.value = result.parfum.id;
            }
            
            hideParfumForm();
            parfumSelect.dispatchEvent(new Event('change'));
        } else {
            Modal.error("Erreur du système", result.detail);
        }
    } catch (e) {
        Modal.error("Problème de connexion", e.message);
    }
};

// --- Gestion Impression Multiple (Batch) 4-up ---
const print4UpBtn = document.getElementById('print-4up-btn');
const addToBatch4UpBtn = document.getElementById('add-to-batch-4up-btn');
const qty4UpInput = document.getElementById('parfum-qty');
const batchList4UpContainer = document.getElementById('batch-list-4up-container');
const batchUl4Up = document.getElementById('batch-list-4up');
const batchTotal4UpSpan = document.getElementById('batch-total-4up');

let batch4Up = [];

function updateBatch4UpUI() {
    batchUl4Up.innerHTML = '';
    let total = 0;
    
    batch4Up.forEach((item, index) => {
        total += item.quantity;
        const li = document.createElement('li');
        li.style.borderBottom = "1px solid #e2e8f0";
        li.style.padding = "5px 0";
        li.style.display = "flex";
        li.style.justifyContent = "space-between";
        li.style.alignItems = "center";
        
        const textSpan = document.createElement('span');
        textSpan.innerHTML = `<strong>${item.quantity}x</strong> ${item.parfumName}`;
        
        const delBtn = document.createElement('button');
        delBtn.innerHTML = '<i data-lucide="trash-2"></i>';
        delBtn.className = "btn btn-danger";
        delBtn.style.padding = "2px 5px";
        delBtn.style.fontSize = "12px";
        delBtn.onclick = () => {
            batch4Up.splice(index, 1);
            updateBatch4UpUI();
        };
        
        li.appendChild(textSpan);
        li.appendChild(delBtn);
        batchUl4Up.appendChild(li);
    });
    
    batchTotal4UpSpan.textContent = total;
    lucide.createIcons();
    
    if (batch4Up.length > 0) {
        batchList4UpContainer.style.display = 'block';
        print4UpBtn.style.display = 'inline-flex';
    } else {
        batchList4UpContainer.style.display = 'none';
        print4UpBtn.style.display = 'none';
    }
}

if (addToBatch4UpBtn) {
    addToBatch4UpBtn.onclick = () => {
        const qty = parseInt(qty4UpInput.value);
        if (isNaN(qty) || qty <= 0) {
            Modal.error("Quantité invalide", "Veuillez indiquer un nombre d'étiquettes supérieur à 0.");
            return;
        }

        const parfumId = parfumSelect.value;
        if (!parfumId) {
            Modal.error("Parfum manquant", "Veuillez choisir un parfum dans la liste.");
            return;
        }

        const parfumName = parfumSelect.options[parfumSelect.selectedIndex].text;
        
        batch4Up.push({
            parfum_id: parfumId,
            parfumName: parfumName,
            quantity: qty
        });
        
        updateBatch4UpUI();
        qty4UpInput.value = 1; // reset
    };
}

if (print4UpBtn) {
    print4UpBtn.onclick = async () => {
        if (!isPrinterReady) {
            Modal.error("Imprimante indisponible", "L'imprimante n'est pas prête. Vérifiez qu'elle est allumée et qu'il n'y a pas d'erreur rouge.");
            return;
        }

        if (batch4Up.length === 0) return;

        const totalQty = batch4Up.reduce((acc, curr) => acc + curr.quantity, 0);
        const recapList = batch4Up.map(b => `- ${b.quantity}x ${b.parfumName}`).join('\n');

        const ok = await Modal.confirm(
            "Confirmation d'impression multiple", 
            `Vous allez lancer l'impression de ${totalQty} étiquettes au total pour les parfums suivants :\n\n${recapList}\n\nUn séparateur sera automatiquement imprimé entre chaque parfum.\n\nÊtes-vous sûr ?`, 
            'printer', 
            'icon-info'
        );
        if (!ok) return;

        addLog(`Lancement impression 4-up (Batch de ${batch4Up.length} parfums, Total: ${totalQty})`);
        
        try {
            const opt = printerSelect.options[printerSelect.selectedIndex];
            
            // On prépare l'objet items sans le champ "parfumName" (qui n'est que pour l'UI)
            const apiItems = batch4Up.map(b => ({
                parfum_id: b.parfum_id,
                quantity: b.quantity
            }));
            
            const response = await fetch('/print-4up', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    printer_ip: opt.value,
                    printer_dpi: parseInt(opt.dataset.dpi),
                    printer_language: opt.dataset.language,
                    items: apiItems,
                    offset_x: parseInt(opt.dataset.offsetX) || 0,
                    offset_y: parseInt(opt.dataset.offsetY) || 0,
                    title_size: parseInt(opt.dataset.titleSize) || 0,
                    title_bold: opt.dataset.titleBold === "true",
                    gs1_size: parseInt(opt.dataset.gs1Size) || 0,
                    gs1_bold: opt.dataset.gs1Bold === "true",
                    lot_size: parseInt(opt.dataset.lotSize) || 0,
                    lot_bold: opt.dataset.lotBold === "true"
                })
            });

            const result = await response.json();
            if (response.ok) {
                addLog(`Succès: ${result.message}`, "success");
                Modal.alert("Impression envoyée", "Les étiquettes sont en cours d'impression !", 'check-circle', 'icon-success');
                // On vide le panier après succès
                batch4Up = [];
                updateBatch4UpUI();
            } else {
                Modal.error("Erreur du système", result.detail);
            }
        } catch (e) {
            Modal.error("Problème de connexion", e.message);
        }
    };
}

// Gestion des imprimantes (Espace Technicien)
const savePrintersBtn = document.getElementById('save-printers-btn');
const managePrintersTableBody = document.querySelector('#manage-printers-table tbody');

let localPrinters = [...printersData];

if (savePrintersBtn) {
    savePrintersBtn.onclick = async () => {
        const ok = await Modal.confirm("Enregistrer les adresses IP", "Voulez-vous appliquer ces nouvelles adresses IP au système ?", 'save', 'icon-warning');
        if (!ok) return;

        try {
            const response = await fetch('/api/printers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(localPrinters)
            });
            if (response.ok) {
                Modal.alert("Sauvegardé", "Les imprimantes ont été mises à jour. L'application va se recharger.", 'check-circle', 'icon-success');
                setTimeout(() => location.reload(), 1500);
            } else {
                Modal.error("Erreur", "Impossible de sauvegarder la configuration.");
            }
        } catch (e) {
            Modal.error("Problème réseau", e.message);
        }
    };
}

function renderManageTable() {
    if (!managePrintersTableBody) return;
    managePrintersTableBody.innerHTML = '';
    localPrinters.forEach((p, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td style="font-weight: 500; color: #475569;">${p.name}</td>
            <td>
                <input type="text" value="${p.ip}" oninput="localPrinters[${index}].ip = this.value" style="font-family: monospace; font-weight: bold; width: 100%;">
            </td>
            <td style="color: #64748b;">${p.dpi} DPI</td>
            <td style="color: #64748b;">${p.language}</td>
            <td style="color: #64748b;">
                <span class="status-badge" style="background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1;">${p.sector}</span>
            </td>
        `;
        managePrintersTableBody.appendChild(tr);
    });
}

function filterPrinters(sector) {
    printerSelect.innerHTML = '';
    const filtered = printersData.filter(p => p.sector === sector);
    filtered.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.ip;
        opt.textContent = `${p.name} (${p.ip})`;
        opt.dataset.dpi = p.dpi;
        opt.dataset.language = p.language || 'ZPL';
        opt.dataset.offsetX = p.offset_x !== undefined ? p.offset_x : (p.language === 'TPCL' ? 0 : 800);
        opt.dataset.offsetY = p.offset_y !== undefined ? p.offset_y : (p.language === 'TPCL' ? 0 : 18);
        // Offsets spécifiques au format 4-up (B-EV4 uniquement, configurés dans printers.json)
        opt.dataset.offsetX4up = p.offset_x_4up !== undefined ? p.offset_x_4up : opt.dataset.offsetX;
        opt.dataset.offsetY4up = p.offset_y_4up !== undefined ? p.offset_y_4up : opt.dataset.offsetY;

        opt.dataset.titleSize = p.title_size || 0;
        opt.dataset.titleBold = !!p.title_bold;
        opt.dataset.gs1Size = p.gs1_size || 0;
        opt.dataset.gs1Bold = !!p.gs1_bold;
        opt.dataset.lotSize = p.lot_size || 0;
        opt.dataset.lotBold = !!p.lot_bold;
        printerSelect.appendChild(opt);
    });
    
    // Afficher ou cacher le bouton de calibrage selon l'imprimante
    const openCalibrationBtn = document.getElementById('open-calibration-btn');
    const openCalibrationHeaderBtn = document.getElementById('open-calibration-header-btn');
    const toggleCalibrationBtn = () => {
        const opt = printerSelect.options[printerSelect.selectedIndex];
        if (openCalibrationBtn) openCalibrationBtn.style.display = 'block';
        if (openCalibrationHeaderBtn) openCalibrationHeaderBtn.style.display = 'flex';
    };
    printerSelect.addEventListener('change', toggleCalibrationBtn);
    toggleCalibrationBtn();
    
    updatePrinterStatus();
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(updatePrinterStatus, 3000);
}

// ==========================================
// Logique de calibrage Zebra 1-up
// ==========================================
const calibrationModal = document.getElementById('calibration-modal');
const closeCalibrationModal = document.getElementById('close-calibration-modal');
const openCalibrationBtn = document.getElementById('open-calibration-btn');
const openCalibrationHeaderBtn = document.getElementById('open-calibration-header-btn');
const calibValX = document.getElementById('calib-val-x'); // Gauche/Droite
const calibValY = document.getElementById('calib-val-y'); // Haut/Bas
const calibImg = document.getElementById('calibration-preview-img');
const saveCalibrationBtn = document.getElementById('save-calibration-btn');
const calibContainer = calibImg.parentElement.parentElement;

const titleSizeInput = document.getElementById('style-title-size');
const titleBoldInput = document.getElementById('style-title-bold');
const gs1SizeInput = document.getElementById('style-gs1-size');
const gs1BoldInput = document.getElementById('style-gs1-bold');
const lotSizeInput = document.getElementById('style-lot-size');
const lotBoldInput = document.getElementById('style-lot-bold');

function getStylingQuery() {
    return `&title_size=${titleSizeInput.value}&title_bold=${titleBoldInput.checked}&gs1_size=${gs1SizeInput.value}&gs1_bold=${gs1BoldInput.checked}&lot_size=${lotSizeInput.value}&lot_bold=${lotBoldInput.checked}`;
}

function updateCalibrationVisual() {
    const zebraY = parseInt(calibValX.value) || 0;
    const zebraX = parseInt(calibValY.value) || 0;
    
    const opt = printerSelect.options[printerSelect.selectedIndex];
    if (opt && opt.dataset.language === 'TPCL') {
        calibImg.style.left = zebraY + 'px';
        calibImg.style.top = zebraX + 'px';
    } else {
        calibImg.style.left = zebraY + 'px';
        calibImg.style.top = (zebraX - 800) + 'px';
    }
}

const calibFormatSelectorGroup = document.getElementById('calib-format-selector-group');
const calibFormatSelector = document.getElementById('calib-format-selector');

function updateCalibrationPreviewImage() {
    const opt = printerSelect.options[printerSelect.selectedIndex];
    if (!opt) return;
    
    const lang = opt.dataset.language;
    const isLigne1 = opt.text.startsWith("Zebra Prépa commande");
    
    const calibBorders = document.getElementById('calib-physical-borders');
    calibBorders.innerHTML = ''; // Réinitialiser
    
    calibContainer.style.opacity = '0.5';
    calibImg.onload = () => {
        calibContainer.style.opacity = '1';
    };
    
    if (lang === 'TPCL') {
        calibFormatSelectorGroup.style.display = 'block';
        const format = calibFormatSelector.value;
        
        if (format === '4up') {
            calibImg.src = `/api/preview-4up-demo?t=${new Date().getTime()}${getStylingQuery()}`;
            calibContainer.style.width = '138px';
            calibContainer.style.height = '320px';
            calibImg.parentElement.style.transform = 'scale(0.4)';
            calibImg.parentElement.style.left = '0px';
            
            // 4-up borders
            const tops = [0, 80, 160, 240];
            tops.forEach(t => {
                const div = document.createElement('div');
                div.style.position = 'absolute';
                div.style.border = '1px dashed #ef4444';
                div.style.left = '0px';
                div.style.top = t + 'px';
                div.style.width = '137.6px';
                div.style.height = '70.4px';
                calibBorders.appendChild(div);
            });
            
        } else {
            calibImg.src = `/api/preview-3up?t=${new Date().getTime()}${getStylingQuery()}`;
            calibContainer.style.width = '368px'; // 920 * 0.4
            calibContainer.style.height = '320px';
            calibImg.parentElement.style.transform = 'scale(0.4)';
            calibImg.parentElement.style.left = '-112px'; // Hide the 280-dots hardware gap (112px)
            
            // 3-up borders
            const tops = [4.8, 107.2, 209.6];
            tops.forEach(t => {
                const div = document.createElement('div');
                div.style.position = 'absolute';
                div.style.border = '1px dashed #ef4444';
                div.style.left = '0px'; // Cropped container, so left is 0
                div.style.top = t + 'px';
                div.style.width = '368px';
                div.style.height = '96px';
                calibBorders.appendChild(div);
            });
        }
    } else if (isLigne1) {
        calibFormatSelectorGroup.style.display = 'block';
        const format = calibFormatSelector.value;
        if (format === '2up') {
            calibImg.src = `/api/preview-zebra-2up?t=${new Date().getTime()}${getStylingQuery()}`;
            calibContainer.style.width = '292px';
            calibContainer.style.height = '74px';
            calibImg.parentElement.style.transform = 'scale(0.4)';
            calibImg.parentElement.style.left = '0px';
            
            // 2-up borders
            const lefts = [0, 150.4];
            lefts.forEach(l => {
                const div = document.createElement('div');
                div.style.position = 'absolute';
                div.style.border = '1px dashed #ef4444';
                div.style.top = '0px';
                div.style.left = l + 'px';
                div.style.width = '140.8px';
                div.style.height = '73.6px';
                calibBorders.appendChild(div);
            });
        } else {
            calibImg.src = `/api/preview-zebra-1up?t=${new Date().getTime()}${getStylingQuery()}`;
            calibContainer.style.width = '286px';
            calibContainer.style.height = '88px';
            calibImg.parentElement.style.transform = 'scale(0.25)';
            calibImg.parentElement.style.left = '0px';
            
            // 1-up borders
            const div = document.createElement('div');
            div.style.position = 'absolute';
            div.style.border = '1px dashed #ef4444';
            div.style.top = '0px';
            div.style.left = '0px';
            div.style.width = '286px';
            div.style.height = '88px';
            calibBorders.appendChild(div);
        }
    } else {
        calibFormatSelectorGroup.style.display = 'none';
        calibImg.src = `/api/preview-zebra-1up?t=${new Date().getTime()}${getStylingQuery()}`;
        calibContainer.style.width = '286px';
        calibContainer.style.height = '88px';
        calibImg.parentElement.style.transform = 'scale(0.25)';
        calibImg.parentElement.style.left = '0px';
        
        // 1-up borders
        const div = document.createElement('div');
        div.style.position = 'absolute';
        div.style.border = '1px dashed #ef4444';
        div.style.top = '0px';
        div.style.left = '0px';
        div.style.width = '286px';
        div.style.height = '88px';
        calibBorders.appendChild(div);
    }
}

calibFormatSelector.onchange = (e) => {
    const val = e.target.value;
    const opt = printerSelect.options[printerSelect.selectedIndex];
    if (opt && opt.text.startsWith('Zebra Prépa commande')) {
        let targetOpt;
        if (val === '2up') {
            targetOpt = Array.from(printerSelect.options).find(o => o.text.includes('x2'));
        } else {
            targetOpt = Array.from(printerSelect.options).find(o => o.text.startsWith('Zebra Prépa commande') && !o.text.includes('x2'));
        }
        if (targetOpt && printerSelect.value !== targetOpt.value) {
            printerSelect.value = targetOpt.value;
            // Reload offsets for this new selected printer
            calibValX.value = targetOpt.dataset.offsetY || 0;
            calibValY.value = targetOpt.dataset.offsetX || 0;
            titleSizeInput.value = targetOpt.dataset.titleSize || 0;
            titleBoldInput.checked = targetOpt.dataset.titleBold === "true";
            gs1SizeInput.value = targetOpt.dataset.gs1Size || 0;
            gs1BoldInput.checked = targetOpt.dataset.gs1Bold === "true";
            lotSizeInput.value = targetOpt.dataset.lotSize || 0;
            lotBoldInput.checked = targetOpt.dataset.lotBold === "true";
        }
    }
    updateCalibrationPreviewImage();
    updateCalibrationVisual();
};

const openCalibrationModal = async () => {
    const opt = printerSelect.options[printerSelect.selectedIndex];
    if (!opt) return;
    
    calibValX.value = opt.dataset.offsetY || 0;
    calibValY.value = opt.dataset.offsetX || 0;
    
    titleSizeInput.value = opt.dataset.titleSize || 0;
    titleBoldInput.checked = opt.dataset.titleBold === "true";
    gs1SizeInput.value = opt.dataset.gs1Size || 0;
    gs1BoldInput.checked = opt.dataset.gs1Bold === "true";
    lotSizeInput.value = opt.dataset.lotSize || 0;
    lotBoldInput.checked = opt.dataset.lotBold === "true";
    
    // Auto-selection of format if it was previously clicked
    if (opt.dataset.language === 'TPCL') {
        const formatBtn = document.querySelector('.format-btn.active');
        const format = formatBtn ? formatBtn.dataset.format : '3up';
        calibFormatSelector.value = (format === '4up') ? '4up' : '3up';
    } else if (opt.text.startsWith('Zebra Prépa commande')) {
        if (opt.text.includes('x2')) {
            calibFormatSelector.value = '2up';
        } else {
            calibFormatSelector.value = '1up';
        }
    }
    updateCalibrationPreviewImage();
    updateCalibrationVisual();
    calibrationModal.style.display = 'flex';
};

if (openCalibrationBtn) openCalibrationBtn.onclick = openCalibrationModal;
if (openCalibrationHeaderBtn) openCalibrationHeaderBtn.onclick = openCalibrationModal;

closeCalibrationModal.onclick = () => {
    calibrationModal.style.display = 'none';
};
    
    document.getElementById('calib-left').onclick = () => { calibValX.value = parseInt(calibValX.value) - 1; updateCalibrationVisual(); };
    document.getElementById('calib-right').onclick = () => { calibValX.value = parseInt(calibValX.value) + 1; updateCalibrationVisual(); };
    document.getElementById('calib-up').onclick = () => { calibValY.value = parseInt(calibValY.value) - 1; updateCalibrationVisual(); };
    document.getElementById('calib-down').onclick = () => { calibValY.value = parseInt(calibValY.value) + 1; updateCalibrationVisual(); };
    
    calibValX.oninput = updateCalibrationVisual;
    calibValY.oninput = updateCalibrationVisual;
    
    let previewDebounce;
    const triggerPreviewUpdate = () => {
        clearTimeout(previewDebounce);
        previewDebounce = setTimeout(updateCalibrationPreviewImage, 500);
    };
    titleSizeInput.oninput = triggerPreviewUpdate;
    titleBoldInput.onchange = triggerPreviewUpdate;
    gs1SizeInput.oninput = triggerPreviewUpdate;
    gs1BoldInput.onchange = triggerPreviewUpdate;
    lotSizeInput.oninput = triggerPreviewUpdate;
    lotBoldInput.onchange = triggerPreviewUpdate;
    
    saveCalibrationBtn.onclick = async () => {
        const opt = printerSelect.options[printerSelect.selectedIndex];
        const newOffsetX = parseInt(calibValY.value);
        const newOffsetY = parseInt(calibValX.value);
        
        try {
            const res = await fetch('/api/update-printer-offsets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ip: opt.value,
                    offset_x: newOffsetX,
                    offset_y: newOffsetY,
                    title_size: parseInt(titleSizeInput.value) || 0,
                    title_bold: titleBoldInput.checked,
                    gs1_size: parseInt(gs1SizeInput.value) || 0,
                    gs1_bold: gs1BoldInput.checked,
                    lot_size: parseInt(lotSizeInput.value) || 0,
                    lot_bold: lotBoldInput.checked
                })
            });
            if (res.ok) {
                // Mettre à jour en local
                opt.dataset.offsetX = newOffsetX;
                opt.dataset.offsetY = newOffsetY;
                opt.dataset.titleSize = titleSizeInput.value;
                opt.dataset.titleBold = titleBoldInput.checked;
                opt.dataset.gs1Size = gs1SizeInput.value;
                opt.dataset.gs1Bold = gs1BoldInput.checked;
                opt.dataset.lotSize = lotSizeInput.value;
                opt.dataset.lotBold = lotBoldInput.checked;
                
                // Mettre à jour aussi dans printersData pour que ce soit persistant si on re-filtre
                const pData = printersData.find(p => p.ip === opt.value);
                if (pData) {
                    pData.offset_x = newOffsetX;
                    pData.offset_y = newOffsetY;
                    pData.title_size = parseInt(titleSizeInput.value) || 0;
                    pData.title_bold = titleBoldInput.checked;
                    pData.gs1_size = parseInt(gs1SizeInput.value) || 0;
                    pData.gs1_bold = gs1BoldInput.checked;
                    pData.lot_size = parseInt(lotSizeInput.value) || 0;
                    pData.lot_bold = lotBoldInput.checked;
                }
                
                Modal.alert("Succès", "Calibrage enregistré !");
                calibrationModal.style.display = 'none';
            } else {
                const errData = await res.json().catch(() => ({}));
                Modal.error("Erreur de calibrage", errData.detail || "Impossible de sauvegarder le calibrage.");
            }
        } catch (e) {
            Modal.error("Erreur", "Problème réseau lors de la sauvegarde.");
        }
    };

async function updatePrinterStatus() {
    const ip = printerSelect.value;
    if (!ip) return;
    try {
        const response = await fetch(`/printer-status?ip=${ip}`);
        const status = await response.json();
        printerStatus.className = 'status-badge';
        if (status.error) {
            printerStatus.innerHTML = '<i data-lucide="wifi-off"></i> Imprimante éteinte ou déconnectée';
            printerStatus.classList.add('status-error');
            isPrinterReady = false;
        } else if (status.ready) {
            printerStatus.innerHTML = '<i data-lucide="check-circle"></i> Prête à imprimer';
            printerStatus.classList.add('status-ready');
            isPrinterReady = true;
        } else {
            printerStatus.innerHTML = '<i data-lucide="alert-triangle"></i> Problème sur l\'imprimante (Papier? Capot ouvert?)';
            printerStatus.classList.add('status-busy');
            isPrinterReady = false;
        }
    } catch (e) {
        printerStatus.innerHTML = '<i data-lucide="x-circle"></i> Erreur de communication';
        printerStatus.classList.add('status-error');
        isPrinterReady = false;
    }
    lucide.createIcons();
}

// Upload CSV Zone
dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('dragover'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length) handleFile(e.dataTransfer.files[0]);
});
fileInput.onchange = () => { 
    if (fileInput.files.length) handleFile(fileInput.files[0]);
    fileInput.value = ''; 
};

// --- NOUVEAU : Logique API ERP ---
const apiOrderInput = document.getElementById('api-order-number');
const apiFetchBtn = document.getElementById('api-fetch-btn');

if (apiFetchBtn) {
    apiFetchBtn.onclick = async () => {
        const orderNumber = apiOrderInput.value.trim();
        if (!orderNumber) {
            Modal.error("Numéro manquant", "Veuillez taper un numéro de commande valide.");
            return;
        }

        const originalText = apiFetchBtn.innerHTML;
        apiFetchBtn.innerHTML = '<i data-lucide="loader-2" class="spin-icon"></i> Recherche...';
        apiFetchBtn.disabled = true;

        try {
            const res = await fetch(`/api/commande/${encodeURIComponent(orderNumber)}`);
            if (res.ok) {
                const data = await res.json();
                
                if (data.length === 0) {
                    Modal.error("Introuvable", `La commande ${orderNumber} n'existe pas ou ne contient aucun produit dans l'ERP.`);
                } else {
                    const aggregated = aggregateOrderData(data);
                    aggregated.forEach(item => item._selected = true);
                    currentData = aggregated;
                    displayEditSection();
                }
            } else if (res.status === 403) {
                 Modal.error("Licence bloquée", "Vous n'avez pas les droits de licence pour utiliser l'API.");
            } else {
                Modal.error("Erreur API", `Impossible de récupérer la commande (Erreur ${res.status}).`);
            }
        } catch (e) {
            Modal.error("Erreur Réseau", e.message);
        } finally {
            apiFetchBtn.innerHTML = originalText;
            apiFetchBtn.disabled = false;
            lucide.createIcons();
        }
    };
    
    // Permettre la validation avec la touche Entrée
    apiOrderInput.addEventListener('keypress', function (e) {
        if (e.key === 'Enter') {
            apiFetchBtn.click();
        }
    });
}
// ---------------------------------

function handleFile(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        let text = e.target.result;
        text = text.replace(/^\uFEFF/, '');
        currentData = parseCSV(text);
        if (currentData.length > 0) {
            displayEditSection();
        } else {
            Modal.error("Problème avec le fichier", "Le fichier semble vide ou ce n'est pas le bon format. Assurez-vous d'utiliser le bon fichier fourni par le système.");
        }
    };
    reader.readAsText(file);
}

function parseCSV(text) {
    const lines = text.split(/\r?\n/).map(l => l.trim()).filter(l => l !== '');
    if (lines.length < 1) return [];
    let headerIndex = lines.findIndex(l => l.toLowerCase().includes('libelle'));
    if (headerIndex === -1) headerIndex = 0;
    const headerLine = lines[headerIndex];
    const headers = headerLine.split(';').map(h => h.trim());
    const dataLines = lines.slice(headerIndex + 1);
    const result = [];
    dataLines.forEach(line => {
        if (line === headerLine) return;
        const values = line.split(';').map(v => v.trim());
        if (values.length < 2) return;
        const obj = { _selected: true };
        headers.forEach((h, i) => { if (h) obj[h] = values[i] || ""; });
        if (obj.Libelle && obj.Libelle.toLowerCase() !== "libelle") result.push(obj);
    });
    return aggregateOrderData(result);
}

function aggregateOrderData(data) {
    if (!data || data.length === 0) return [];
    
    const aggregated = [];
    const map = new Map();
    
    data.forEach(item => {
        const lib = item.Libelle || item.Designation || "";
        const dateKey = item.CodeBarre17 || item.Numlot || "";
        if (!lib) return; 
        
        const key = lib + "_" + dateKey;
        
        if (map.has(key)) {
            const existing = map.get(key);
            existing.Quantite = (parseInt(existing.Quantite) || 0) + (parseInt(item.Quantite) || 0);
        } else {
            const clone = { ...item };
            clone.Quantite = parseInt(item.Quantite) || 0;
            map.set(key, clone);
            aggregated.push(clone);
        }
    });
    
    // Règle CREMLOG / CREMCENTRE : Les couches doivent être pleines (arrondi au supérieur)
    const client = data[0].Client ? data[0].Client.toUpperCase() : "";
    if (client.includes("CREMLOG") || client.includes("CREMCENTRE")) {
        // Grouper par Libellé (ignorer DLC) pour avoir le total par parfum
        const totalParParfum = {};
        aggregated.forEach(item => {
            const lib = item.Libelle || item.Designation;
            if (!totalParParfum[lib]) totalParParfum[lib] = { qte: 0, firstItem: item };
            totalParParfum[lib].qte += item.Quantite;
        });
        
        for (const lib in totalParParfum) {
            let colisParCouche = 1;
            const libLower = lib.toLowerCase();
            
            // Déduction du nombre par couche selon le libellé
            if (libLower.includes("paraffine")) {
                colisParCouche = 1; // Pas d'arrondi
            } else if (libLower.includes("140g") || libLower.includes("brasse") || libLower.includes("brassé")) {
                colisParCouche = 36;
            } else if (libLower.includes("125g")) {
                colisParCouche = 18;
            } else if (libLower.includes("skyr")) {
                colisParCouche = 13;
            }
            
            const total = totalParParfum[lib].qte;
            if (colisParCouche > 1 && total % colisParCouche !== 0) {
                const newTotal = Math.ceil(total / colisParCouche) * colisParCouche;
                const diff = newTotal - total;
                // On ajoute la différence à la première ligne trouvée pour ce parfum
                totalParParfum[lib].firstItem.Quantite += diff;
            }
        }
    }
    
    return aggregated;
}

function displayEditSection() {
    if (currentData.length === 0) return;
    orderClient.innerHTML = `<i data-lucide="user"></i> Client : ${currentData[0].Client || 'Inconnu'}`;
    orderId.innerHTML = `<i data-lucide="file-text"></i> Commande : ${currentData[0].Commande || 'Inconnue'}`;
    
    productsTableBody.innerHTML = '';
    
    const opt = printerSelect.options[printerSelect.selectedIndex];
    const isLigne1 = opt && opt.text.startsWith("Zebra Prépa commande") && !opt.text.includes("x2");
    
    const thQuantite = document.getElementById('th-quantite');
    const thQuantitePots = document.getElementById('th-quantite-pots');
    
    if (isLigne1) {
        // Préserver l'état des cases à cocher lors des rechargements (ex: suppression de ligne)
        const cartonWasChecked = document.getElementById('enable-carton') ? document.getElementById('enable-carton').checked : true;
        const potsWasChecked = document.getElementById('enable-pots') ? document.getElementById('enable-pots').checked : true;
        
        thQuantite.innerHTML = `<div style="display:flex; align-items:center; gap:5px; justify-content:flex-start;"><input type="checkbox" id="enable-carton" ${cartonWasChecked ? 'checked' : ''} class="large-checkbox" title="Activer/Désactiver l'impression Carton"> <i data-lucide="box"></i> Qte Carton</div>`;
        thQuantite.style.backgroundColor = '#e0e7ff';
        thQuantite.style.color = '#3730a3';
        
        thQuantitePots.innerHTML = `<div style="display:flex; align-items:center; gap:5px; justify-content:flex-start;"><input type="checkbox" id="enable-pots" ${potsWasChecked ? 'checked' : ''} class="large-checkbox" title="Activer/Désactiver l'impression Pots x2"> <i data-lucide="box"></i> Qte Pots x2</div>`;
        thQuantitePots.style.display = '';
    } else {
        thQuantite.textContent = 'Quantité';
        thQuantite.style.backgroundColor = '';
        thQuantite.style.color = '';
        thQuantitePots.style.display = 'none';
    }
    
    currentData.forEach((item, index) => {
        if (isLigne1 && item.QuantitePots === undefined) {
            item.QuantitePots = (parseInt(item.Quantite) || 0) * 6;
        }
        
        let qteCartonCol = `<input type="number" value="${item.Quantite || 0}" style="${isLigne1 ? 'background-color: #eef2ff; border-color: #c7d2fe; font-weight: bold; color: #3730a3;' : ''}" oninput="updateRowData(${index}, 'Quantite', this.value)">`;
        let extraCol = isLigne1 ? `<td style="background-color: #f0fdf4;"><input type="number" id="qte-pots-${index}" value="${item.QuantitePots || 0}" style="background-color: #dcfce7; border-color: #bbf7d0; font-weight: bold; color: #166534;" oninput="updateRowData(${index}, 'QuantitePots', this.value)"></td>` : '<td style="display:none;"></td>';
        
        const rawDLC = item.CodeBarre17 || item.DateLivraison || '';
        let displayDLC = rawDLC;
        if (rawDLC && rawDLC.length === 6 && !rawDLC.includes('/')) {
            displayDLC = `${rawDLC.substring(4,6)}/${rawDLC.substring(2,4)}/20${rawDLC.substring(0,2)}`;
        }
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="row-select large-checkbox" ${item._selected ? 'checked' : ''} oninput="updateRowData(${index}, '_selected', this.checked)"></td>
            <td><strong>${item.Libelle}</strong></td>
            <td><input type="text" value="${displayDLC}" onchange="updateDLC(${index}, this.value)"></td>
            <td><input type="text" value="${item.Numlot || ''}" oninput="updateRowData(${index}, 'Numlot', this.value)"></td>
            <td style="${isLigne1 ? 'background-color: #f5f8ff;' : ''}">${qteCartonCol}</td>
            ${extraCol}
            <td><button class="btn-remove" onclick="removeLine(${index})" title="Retirer cette ligne"><i data-lucide="trash-2"></i></button></td>
        `;
        productsTableBody.appendChild(tr);
    });
    
    lucide.createIcons();
    
    uploadSection.style.display = 'none';
    editSection.style.display = 'block';
    editSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

window.updateDLC = (index, displayValue) => {
    let rawValue = displayValue.trim();
    // Si l'utilisateur a tapé DD/MM/YYYY, on le remet en YYMMDD pour le ZPL
    if (rawValue.includes('/')) {
        const parts = rawValue.split('/');
        if (parts.length === 3) {
            let yy = parts[2];
            if (yy.length === 4) yy = yy.substring(2, 4);
            rawValue = `${yy}${parts[1]}${parts[0]}`;
        }
    }
    updateRowData(index, 'CodeBarre17', rawValue);
}

window.updateRowData = (index, field, value) => {
    if (field === 'Quantite' || field === 'QuantitePots') value = parseInt(value) || 0;
    if (currentData[index]) {
        currentData[index][field] = value;
        if (field === 'Quantite') {
            const potsInput = document.getElementById(`qte-pots-${index}`);
            if (potsInput) {
                const newPots = value * 6;
                currentData[index]['QuantitePots'] = newPots;
                potsInput.value = newPots;
            }
        }
    }
};

selectAllCheckbox.onchange = () => {
    const isChecked = selectAllCheckbox.checked;
    currentData.forEach(item => item._selected = isChecked);
    displayEditSection();
};

window.removeLine = async (index) => {
    const ok = await Modal.confirm("Retirer la ligne", "Voulez-vous vraiment empêcher l'impression de cette ligne ?", 'trash-2', 'icon-warning');
    if (ok) {
        currentData.splice(index, 1);
        if (currentData.length === 0) closeEditSection();
        else displayEditSection();
    }
};

cancelBtn.onclick = async () => {
    if (isPrinting || currentData.length === 0) {
        closeEditSection();
        return;
    }

    const ok = await Modal.confirm("Annuler", "Voulez-vous fermer ce fichier sans l'imprimer ?", 'x-circle', 'icon-error');
    if (ok) {
        closeEditSection();
    }
};

function closeEditSection() {
    editSection.style.display = 'none';
    uploadSection.style.display = 'block';
    fileInput.value = '';
    currentData = [];
    isPrinting = false;
    step3.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

printBtn.onclick = () => startPrint(false);
printAllBtn.onclick = () => startPrint(true);

const btnPaletisationOrder = document.getElementById('btn-paletisation-order');
const paletisationModal = document.getElementById('paletisation-modal');
const closePaletisationModal = document.getElementById('close-paletisation-modal');
const paletisationContainer = document.getElementById('paletisation-container');
const paletisationSummary = document.getElementById('paletisation-summary');

if (closePaletisationModal) {
    closePaletisationModal.onclick = () => {
        paletisationModal.style.display = 'none';
    };
}

if (btnPaletisationOrder) {
    btnPaletisationOrder.onclick = async () => {
        if (!currentData || currentData.length === 0) return;
        
        // Grouper les quantités par libellé au cas où il y ait des doublons
        const grouped = {};
        currentData.forEach(item => {
            // On prend toutes les lignes, cochées ou non
            const lib = item.Libelle || item.Designation || "Inconnu";
            const qte = parseInt(item.Quantite) || 0;
            if (!grouped[lib]) grouped[lib] = 0;
            grouped[lib] += qte;
        });

        const items = Object.keys(grouped).map(lib => ({
            libelle: lib,
            quantite: grouped[lib]
        })).filter(i => i.quantite > 0);

        const optMaxCheckbox = document.getElementById('opt-max-checkbox');
        const isOptMax = optMaxCheckbox ? optMaxCheckbox.checked : false;

        paletisationSummary.innerHTML = '<i data-lucide="loader-2" class="spin-icon"></i> Calcul du plan optimal...';
        paletisationContainer.innerHTML = '';
        paletisationModal.style.display = 'flex';
        lucide.createIcons();

        try {
            const response = await fetch('/api/palettisation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ items: items, optimisation_max: isOptMax })
            });
            const result = await response.json();
            
            if (result.success) {
                let totalPalettes = 0;
                let totalPoids = 0;
                let summaryHTML = `<div style="margin-bottom:10px; display: flex; justify-content: space-around;">
                    <div><strong>Total Palettes au sol :</strong> ${result.tours.length}</div>
                    <div><strong>Total Palettes bois :</strong> <span id="total-pal-count"></span></div>
                    <div><strong>Poids total estimé :</strong> <span id="total-weight-count"></span> kg</div>
                </div>
                <div style="font-size: 13px; display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; border-top: 1px solid #e2e8f0; padding-top: 10px;" id="paletisation-details">`;

                // On passe le conteneur principal en Grid
                paletisationContainer.style.display = 'grid';
                paletisationContainer.style.gridAutoFlow = 'column';
                paletisationContainer.style.gridAutoColumns = '160px';
                paletisationContainer.style.gap = '20px';
                
                // Dessin graphique
                const cmToPx = 2.5; 
                
                result.tours.forEach((tour, i) => {
                    // Utilisation du poids réel calculé par le backend
                    const tourPoids = tour.poids_kg || 0;
                    totalPoids += tourPoids;
                    totalPalettes += tour.items.length;
                    
                    summaryHTML += `<div><strong>n°${i+1} :</strong> ${tourPoids.toFixed(1)} kg</div>`;

                    let hauteurTxt = document.createElement('div');
                    hauteurTxt.style.textAlign = 'center';
                    hauteurTxt.style.marginBottom = '10px';
                    hauteurTxt.style.color = '#475569';
                    hauteurTxt.style.alignSelf = 'end'; // Aligné en bas de sa cellule
                    hauteurTxt.innerHTML = `<strong style="color: #9333ea; font-size: 15px;">n°${i+1}</strong><br><span style="font-weight: bold;">${tour.hauteur} cm</span>`;
                    
                    // On va créer un conteneur pour la tour
                    const tourStack = document.createElement('div');
                    tourStack.style.display = 'flex';
                    tourStack.style.flexDirection = 'column-reverse';
                    tourStack.style.width = '100%';
                    
                    tour.items.forEach(pal => {
                        // Dessiner la palette bois en dessous (hauteur visuelle divisée par 2)
                        const bois = document.createElement('div');
                        bois.style.height = `${(14.5 / 2) * cmToPx}px`; 
                        bois.style.width = '100%';
                        bois.style.background = '#8b4513';
                        bois.style.borderRadius = '2px';
                        bois.style.marginTop = '2px';
                        bois.title = "Palette Bois (14.5 cm)";
                        
                        // Dessiner le bloc produit
                        const bloc = document.createElement('div');
                        // On force une hauteur minimale de 36px pour être sûr de pouvoir afficher le texte
                        const visualHeight = Math.max(36, pal.hauteur_cm * cmToPx);
                        bloc.style.height = `${visualHeight}px`;
                        bloc.style.width = '100%';
                        bloc.style.borderRadius = '4px';
                        bloc.style.border = '1px solid rgba(0,0,0,0.2)';
                        bloc.style.display = 'flex';
                        bloc.style.flexDirection = 'column';
                        bloc.style.alignItems = 'center';
                        bloc.style.justifyContent = 'center';
                        bloc.style.color = 'white';
                        bloc.style.textAlign = 'center';
                        bloc.style.padding = '2px';
                        bloc.style.boxSizing = 'border-box';
                        bloc.style.lineHeight = '1.1';
                        bloc.style.marginTop = '2px';
                        bloc.style.overflow = 'hidden';
                        
                        if (pal.famille === 'A') bloc.style.background = '#3b82f6';
                        else if (pal.famille === 'B') bloc.style.background = '#10b981';
                        else if (pal.famille === 'C') bloc.style.background = '#f59e0b';
                        else bloc.style.background = '#64748b';
                        
                        if (pal.fragile) bloc.style.border = '2px dashed #dc2626';
                        
                        let shortName = pal.libelle.substring(0, 25);
                        if (pal.libelle.length > 25) shortName += '...';
                        
                        // Le texte est toujours affiché car le bloc fait au minimum 36px
                        const updateBlocText = () => {
                            bloc.innerHTML = `<strong style="font-size: 12px;">${pal.qte} colis</strong><span style="font-size: 10px; opacity: 0.9;">${shortName}</span><div style="font-size:9px; margin-top:2px;">(${Math.ceil(pal.qte / pal.colis_par_couche)} couches)</div>`;
                            bloc.title = `${pal.qte} cartons de ${pal.libelle} (${pal.pleine ? 'Pleine' : 'Chute'})`;
                        };
                        updateBlocText();
                        
                        bloc.style.cursor = 'pointer';
                        bloc.onclick = () => {
                            openRuptureModal(pal, updateBlocText);
                        };
                        
                        // L'ordre d'ajout dans 'column-reverse' détermine ce qui est en bas.
                        // On ajoute le bois EN PREMIER pour qu'il soit tout en bas physiquement.
                        tourStack.appendChild(bois);
                        tourStack.appendChild(bloc);
                    });
                    
                    let col = document.createElement('div');
                    col.style.display = 'grid';
                    col.style.gridTemplateRows = '1fr auto auto';
                    col.style.height = '100%';
                    col.style.gap = '5px';
                    
                    let spacer = document.createElement('div');
                    
                    col.appendChild(spacer);
                    col.appendChild(hauteurTxt);
                    col.appendChild(tourStack);
                    
                    paletisationContainer.appendChild(col);
                });
                
                summaryHTML += `</div>`;
                paletisationSummary.innerHTML = summaryHTML;
                document.getElementById('total-pal-count').innerText = totalPalettes;
                document.getElementById('total-weight-count').innerText = totalPoids.toFixed(1);
                
            } else {
                paletisationSummary.innerHTML = `<span style="color: red;">Erreur: ${result.error}</span>`;
            }
        } catch (e) {
            paletisationSummary.innerHTML = `<span style="color: red;">Erreur réseau: ${e.message}</span>`;
        }
    };
}

async function startPrint(all = false) {
    if (!isPrinterReady) {
        Modal.error("Imprimante indisponible", "L'imprimante n'est pas prête. Veuillez vérifier l'écran de l'imprimante.");
        return;
    }

    const updatedData = currentData.filter(item => all || item._selected);

    if (updatedData.length === 0) {
        Modal.alert("Rien à imprimer", "Vous devez sélectionner (cocher) au moins une ligne à imprimer.", 'alert-circle', 'icon-warning');
        return;
    }

    const ok = await Modal.confirm("Démarrer l'impression", `Vous allez envoyer ${updatedData.length} produits à l'imprimante.\nTout est correct ?`, 'printer', 'icon-info');
    if (!ok) return;

    isPrinting = true;
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Transfert vers l\'imprimante en cours...';
    
    progressContainer.scrollIntoView({ behavior: 'smooth', block: 'center' });

    try {
        const opt = printerSelect.options[printerSelect.selectedIndex];
        const isLigne1 = opt && opt.text.startsWith("Zebra Prépa commande") && !opt.text.includes("x2");
        
        let payloads = [];
        
        const cartonEnabled = !isLigne1 || (document.getElementById('enable-carton') && document.getElementById('enable-carton').checked);
        const potsEnabled = isLigne1 && (document.getElementById('enable-pots') && document.getElementById('enable-pots').checked);
        
        if (cartonEnabled) {
            payloads.push({
                printer_ip: printerSelect.value,
                printer_dpi: parseInt(opt.dataset.dpi),
                printer_language: opt.dataset.language,
                offset_x: !isNaN(parseInt(opt.dataset.offsetX)) ? parseInt(opt.dataset.offsetX) : (opt.dataset.language === 'TPCL' ? 0 : 800),
                offset_y: !isNaN(parseInt(opt.dataset.offsetY)) ? parseInt(opt.dataset.offsetY) : (opt.dataset.language === 'TPCL' ? 0 : 18),
                title_size: parseInt(opt.dataset.titleSize) || 0,
                title_bold: opt.dataset.titleBold === "true",
                gs1_size: parseInt(opt.dataset.gs1Size) || 0,
                gs1_bold: opt.dataset.gs1Bold === "true",
                lot_size: parseInt(opt.dataset.lotSize) || 0,
                lot_bold: opt.dataset.lotBold === "true",
                items: updatedData
            });
        }
        
        if (potsEnabled) {
            const opt2 = Array.from(printerSelect.options).find(o => o.text.startsWith("Zebra Prépa commande x2"));
            if (opt2) {
                let potsData = updatedData.map(item => {
                    let clone = {...item};
                    clone.Quantite = clone.QuantitePots;
                    return clone;
                }).filter(item => item.Quantite > 0);
                
                if (potsData.length > 0) {
                    payloads.push({
                        printer_ip: opt2.value,
                        printer_dpi: parseInt(opt2.dataset.dpi),
                        printer_language: opt2.dataset.language,
                        offset_x: !isNaN(parseInt(opt2.dataset.offsetX)) ? parseInt(opt2.dataset.offsetX) : (opt2.dataset.language === 'TPCL' ? 0 : 800),
                        offset_y: !isNaN(parseInt(opt2.dataset.offsetY)) ? parseInt(opt2.dataset.offsetY) : (opt2.dataset.language === 'TPCL' ? 0 : 18),
                        title_size: parseInt(opt2.dataset.titleSize) || 0,
                        title_bold: opt2.dataset.titleBold === "true",
                        gs1_size: parseInt(opt2.dataset.gs1Size) || 0,
                        gs1_bold: opt2.dataset.gs1Bold === "true",
                        lot_size: parseInt(opt2.dataset.lotSize) || 0,
                        lot_bold: opt2.dataset.lotBold === "true",
                        items: potsData
                    });
                }
            }
        }
        
        if (payloads.length === 0) {
            Modal.error("Erreur", "Aucune imprimante sélectionnée. Veuillez cocher au moins une colonne.");
            isPrinting = false;
            progressContainer.style.display = 'none';
            return;
        }
        
        for (const payload of payloads) {
            const response = await fetch('/print-json', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || "Erreur d'impression");
            addLog(`Succès (${payload.printer_ip}): ${result.message}`, "success");
        }
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Impression envoyée avec succès ! Vous pouvez regarder les imprimantes.';
        
        setTimeout(() => {
            progressContainer.style.display = 'none';
            isPrinting = false;
            if (!all) {
                currentData.forEach(item => item._selected = false);
                selectAllCheckbox.checked = false;
                displayEditSection();
            }
        }, 4000);
    } catch (e) {
        isPrinting = false;
        Modal.error("Problème réseau", e.message);
        progressContainer.style.display = 'none';
    }
}


function addLog(message, type = "") {
    const wrapper = document.createElement('div');
    wrapper.className = `log-entry-wrapper ${type ? 'log-wrapper-' + type : ''}`;
    
    const time = document.createElement('div');
    time.className = 'log-time';
    const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    time.textContent = now;
    
    const bubble = document.createElement('div');
    bubble.className = 'log-bubble';
    
    let iconStr = '';
    if (type === 'success') iconStr = '<i data-lucide="check" style="width:18px; height:18px; margin-right:8px;"></i> ';
    else if (type === 'error') iconStr = '<i data-lucide="alert-triangle" style="width:18px; height:18px; margin-right:8px;"></i> ';
    else if (type === 'warning') iconStr = '<i data-lucide="alert-circle" style="width:18px; height:18px; margin-right:8px;"></i> ';
    
    bubble.innerHTML = `${iconStr}${message}`;
    
    wrapper.appendChild(time);
    wrapper.appendChild(bubble);
    
    logs.appendChild(wrapper);
    
    // Auto-scroll vers le bas comme un vrai chat
    logs.scrollTop = logs.scrollHeight;
    
    lucide.createIcons();
}

// ==========================================
// WebSocket pour le Spooler d'impression
// ==========================================
let ws = null;
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.type === "status") {
                if (data.level === "error") {
                    addLog(`[${data.ip}] ${data.message}`, "error");
                    if (printerStatus) {
                        printerStatus.innerHTML = `<span style="color:var(--error-color)"><i data-lucide="alert-triangle"></i> ${data.message}</span>`;
                        lucide.createIcons();
                    }
                } else if (data.level === "warning") {
                    addLog(`[${data.ip}] ${data.message}`, "warning");
                    if (printerStatus) {
                        printerStatus.innerHTML = `<span style="color:var(--warning-color, orange)"><i data-lucide="alert-circle"></i> ${data.message}</span>`;
                        lucide.createIcons();
                    }
                } else {
                    addLog(`[${data.ip}] ${data.message}`, "success");
                    if (printerStatus) {
                        printerStatus.innerHTML = `<span style="color:var(--success-color)"><i data-lucide="check-circle"></i> ${data.message}</span>`;
                        lucide.createIcons();
                    }
                }
            }
        } catch (e) {
            console.error("Erreur parsing WS:", e);
        }
    };
    
    ws.onclose = () => {
        setTimeout(connectWebSocket, 5000); // Reconnexion auto
    };
}
connectWebSocket();

document.addEventListener('DOMContentLoaded', () => {
    const optMaxCb = document.getElementById('opt-max-checkbox');
    if (optMaxCb) {
        optMaxCb.addEventListener('change', () => {
            if (document.getElementById('paletisation-modal').style.display === 'flex') {
                openPaletisationModal();
            }
        });
    }

    // Modal Rupture
    const closeRuptureBtn = document.getElementById('close-rupture-modal');
    const cancelRuptureBtn = document.getElementById('btn-cancel-rupture');
    const saveRuptureBtn = document.getElementById('btn-save-rupture');
    const deleteRuptureBtn = document.getElementById('btn-delete-rupture');

    if (closeRuptureBtn) closeRuptureBtn.onclick = () => document.getElementById('rupture-modal').style.display = 'none';
    if (cancelRuptureBtn) cancelRuptureBtn.onclick = () => document.getElementById('rupture-modal').style.display = 'none';
    if (saveRuptureBtn) {
        saveRuptureBtn.onclick = () => {
            const val = parseInt(document.getElementById('rupture-qte-input').value);
            applyRupture(val);
        };
    }
    if (deleteRuptureBtn) {
        deleteRuptureBtn.onclick = () => {
            applyRupture(0);
        };
    }
});

let currentRupturePal = null;
let currentUpdateBlocText = null;

function openRuptureModal(pal, updateBlocTextFn) {
    currentRupturePal = pal;
    currentUpdateBlocText = updateBlocTextFn;
    
    document.getElementById('rupture-title').innerText = `Rupture / Ajustement - ${pal.libelle}`;
    document.getElementById('rupture-subtitle').innerText = `Quantité actuelle dans ce bloc : ${pal.qte} colis (${Math.ceil(pal.qte / pal.colis_par_couche)} couches).`;
    const input = document.getElementById('rupture-qte-input');
    input.value = pal.qte;
    
    document.getElementById('rupture-modal').style.display = 'flex';
    setTimeout(() => input.focus(), 50);
}

function showToast(message) {
    let toast = document.getElementById('toast-container');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-container';
        toast.style.position = 'fixed';
        toast.style.bottom = '20px';
        toast.style.right = '20px';
        toast.style.backgroundColor = '#333';
        toast.style.color = 'white';
        toast.style.padding = '12px 20px';
        toast.style.borderRadius = '8px';
        toast.style.zIndex = '9999';
        toast.style.transition = 'opacity 0.3s ease';
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.opacity = '1';
    toast.style.display = 'block';
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.style.display = 'none', 300);
    }, 3000);
}

function applyRupture(newQte) {
    if (!currentRupturePal) return;
    const pal = currentRupturePal;
    document.getElementById('rupture-modal').style.display = 'none';
    
    if (isNaN(newQte) || newQte < 0) return;
    const diff = pal.qte - newQte;
    if (diff === 0) return;
    
    if (currentData) {
        let remainingDiff = diff;
        for (let d of currentData) {
            const dLib = d.Libelle || d.Designation || "Inconnu";
            if (dLib === pal.libelle) {
                const curQte = parseInt(d.Quantite) || 0;
                if (curQte >= remainingDiff) {
                    d.Quantite = (curQte - remainingDiff).toString();
                    remainingDiff = 0;
                    break;
                } else {
                    remainingDiff -= curQte;
                    d.Quantite = "0";
                }
            }
        }
    }
    
    showToast(`Recalcul de la palettisation en cours...`);
    document.getElementById('btn-paletisation-order').click();
}
