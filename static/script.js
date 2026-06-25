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
const stopBtn = document.getElementById('stop-btn');

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
    step2.style.display = 'none';
    step3.style.display = 'none';
    uploadSection.style.display = 'none';
    parfumSection.style.display = 'none';
    editSection.style.display = 'none';
    progressContainer.style.display = 'none';
    
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
const hubSectorBtns = document.querySelectorAll('.hub-sector-btn');
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

// Au chargement initial (Restore state from URL)
window.addEventListener('DOMContentLoaded', () => {
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
    wizardSection.style.display = 'none';
    logContainer.style.display = 'block';

    const helpBtn = document.getElementById('help-modal-btn');
    if (helpBtn) helpBtn.style.display = 'none';

    if (tool === 'expert') {
        wizardSection.style.display = 'block';
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'none';
        activateSector(sector, false);
        return;
    }

    // Configurer l'imprimante (en fond) pour le secteur
    filterPrinters(sector);

    if (tool === 'toshiba_3up' || tool === 'toshiba_4up') {
        if (helpBtn) helpBtn.style.display = 'block'; // Affiche l'aide Toshiba
        
        // Sélectionne l'imprimante TPCL parmi celles du secteur
        const toshiba = Array.from(printerSelect.options).find(opt => opt.dataset.language === 'TPCL');
        if (toshiba) {
            printerSelect.value = toshiba.value;
            updatePrinterStatus();
        } else {
            Modal.error("Imprimante introuvable", "Aucune imprimante Toshiba n'est configurée pour ce secteur !");
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
    } else if (tool === 'zebra' || tool === 'zebra_prepa' || tool === 'zebra_condi') {
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'none';
        Modal.alert("En construction", "L'interface Zebra arrive cet après-midi !", "clock", "icon-warning");
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

// Gestion du formulaire "Nouveau Parfum"
const toggleAddParfumBtn = document.getElementById('toggle-add-parfum-btn');
const addParfumForm = document.getElementById('add-parfum-form');
const newParfumNom = document.getElementById('new-parfum-nom');
const newParfumEan = document.getElementById('new-parfum-ean');
const previewNewParfumBtn = document.getElementById('preview-new-parfum-btn');
const saveNewParfumBtn = document.getElementById('save-new-parfum-btn');

toggleAddParfumBtn.onclick = () => {
    if (addParfumForm.style.display === 'none') {
        addParfumForm.style.display = 'block';
        toggleAddParfumBtn.innerHTML = '<i data-lucide="x"></i> Fermer ce menu';
    } else {
        addParfumForm.style.display = 'none';
        toggleAddParfumBtn.innerHTML = '<i data-lucide="plus-circle"></i> Nouveau';
    }
    lucide.createIcons();
};

previewNewParfumBtn.onclick = () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    
    if (!nom || !ean) {
        Modal.error("Informations manquantes", "Veuillez taper le nom et le code barre EAN-13.");
        return;
    }
    
    if (ean.length < 13) {
        Modal.error("Code barre incorrect", "Le code barre doit contenir au moins 13 chiffres.");
        return;
    }
    
    parfumPreviewImg.src = `/api/preview-4up-live?nom=${encodeURIComponent(nom)}&ean13=${encodeURIComponent(ean)}&t=${new Date().getTime()}`;
    parfumPreviewImg.style.display = 'inline-block';
    parfumPreviewEmpty.style.display = 'none';
};

saveNewParfumBtn.onclick = async () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    
    if (!nom || !ean) {
        Modal.error("Informations manquantes", "Veuillez taper le nom et le code barre EAN-13.");
        return;
    }
    
    try {
        const response = await fetch('/api/parfums-4up', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nom, ean13: ean })
        });
        
        const result = await response.json();
        if (response.ok) {
            Modal.alert("Enregistré !", "Le nouveau parfum a été sauvegardé avec succès.", 'check-circle', 'icon-success');
            
            const opt = document.createElement('option');
            opt.value = result.parfum.id;
            opt.textContent = `${result.parfum.nom}`;
            parfumSelect.appendChild(opt);
            parfumSelect.value = result.parfum.id;
            
            addParfumForm.style.display = 'none';
            toggleAddParfumBtn.innerHTML = '<i data-lucide="plus-circle"></i> Nouveau';
            lucide.createIcons();
            
            parfumSelect.dispatchEvent(new Event('change'));
        } else {
            Modal.error("Erreur du système", result.detail);
        }
    } catch (e) {
        Modal.error("Problème de connexion", e.message);
    }
};

// Bouton impression 4-up
const print4UpBtn = document.getElementById('print-4up-btn');
const parfumQtyInput = document.getElementById('parfum-qty');

if (print4UpBtn) {
    print4UpBtn.onclick = async () => {
        if (!isPrinterReady) {
            Modal.error("Imprimante indisponible", "L'imprimante n'est pas prête. Vérifiez qu'elle est allumée et qu'il n'y a pas d'erreur rouge.");
            return;
        }

        const qty = parseInt(parfumQtyInput.value);
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
        const ok = await Modal.confirm("Confirmation d'impression", `Vous allez lancer l'impression de ${qty} étiquettes pour le parfum :\n\n${parfumName}\n\nÊtes-vous sûr ?`, 'printer', 'icon-info');
        if (!ok) return;

        addLog(`Lancement impression 4-up (${qty} ex. - ${parfumName})`);
        
        try {
            const response = await fetch('/print-4up', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    printer_ip: printerSelect.value,
                    printer_dpi: parseInt(printerSelect.options[printerSelect.selectedIndex].dataset.dpi),
                    printer_language: printerSelect.options[printerSelect.selectedIndex].dataset.language,
                    parfum_id: parfumId,
                    quantity: qty
                })
            });

            const result = await response.json();
            if (response.ok) {
                addLog(`Succès: ${result.message}`, "success");
                Modal.alert("Impression envoyée", "Les étiquettes sont en cours d'impression !", 'check-circle', 'icon-success');
            } else {
                Modal.error("Erreur du système", result.detail);
            }
        } catch (e) {
            Modal.error("Problème de connexion", e.message);
        }
    };
}

// Modale d'Aide
const helpModal = document.getElementById('help-modal');
const helpModalBtn = document.getElementById('help-modal-btn');
const closeHelpModalBtn = document.getElementById('close-help-modal');

if (helpModalBtn) {
    helpModalBtn.addEventListener('click', () => {
        helpModal.style.display = 'flex';
    });
}
if (closeHelpModalBtn) {
    closeHelpModalBtn.addEventListener('click', () => {
        helpModal.style.display = 'none';
    });
}

// Gestion des imprimantes (Modal Technicien)
const printerModal = document.getElementById('printer-modal');
const managePrintersBtn = document.getElementById('manage-printers-btn');
const closePrinterModalBtn = document.getElementById('close-printer-modal');
const savePrintersBtn = document.getElementById('save-printers-btn');
const addPrinterBtn = document.getElementById('add-printer-btn');
const managePrintersTableBody = document.querySelector('#manage-printers-table tbody');

let localPrinters = [...printersData];

managePrintersBtn.addEventListener('click', () => {
    localPrinters = [...printersData];
    renderManageTable();
    printerModal.style.display = 'flex';
});

closePrinterModalBtn.onclick = () => {
    printerModal.style.display = 'none';
};

addPrinterBtn.onclick = () => {
    localPrinters.push({ name: "Nouvelle machine", ip: "0.0.0.0", dpi: 203, language: "ZPL", sector: "prepa_commande", port: 9100 });
    renderManageTable();
};

savePrintersBtn.onclick = async () => {
    const ok = await Modal.confirm("Enregistrer", "Voulez-vous enregistrer ces paramètres d'imprimantes ?", 'save', 'icon-warning');
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

function renderManageTable() {
    managePrintersTableBody.innerHTML = '';
    localPrinters.forEach((p, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" value="${p.name}" oninput="localPrinters[${index}].name = this.value"></td>
            <td><input type="text" value="${p.ip}" oninput="localPrinters[${index}].ip = this.value"></td>
            <td><input type="number" value="${p.dpi}" oninput="localPrinters[${index}].dpi = parseInt(this.value)"></td>
            <td>
                <select onchange="localPrinters[${index}].language = this.value" style="padding: 8px;">
                    <option value="ZPL" ${p.language === 'ZPL' ? 'selected' : ''}>ZPL (Zebra)</option>
                    <option value="TPCL" ${p.language === 'TPCL' ? 'selected' : ''}>TPCL (Toshiba)</option>
                </select>
            </td>
            <td>
                <select onchange="localPrinters[${index}].sector = this.value" style="padding: 8px;">
                    <option value="prepa_commande" ${p.sector === 'prepa_commande' ? 'selected' : ''}>Prépa Commande</option>
                    <option value="conditionnement" ${p.sector === 'conditionnement' ? 'selected' : ''}>Conditionnement</option>
                </select>
            </td>
            <td><button class="btn-remove" onclick="removePrinter(${index})"><i data-lucide="trash-2"></i></button></td>
        `;
        managePrintersTableBody.appendChild(tr);
    });
    lucide.createIcons();
}

window.removePrinter = (index) => {
    localPrinters.splice(index, 1);
    renderManageTable();
};

function filterPrinters(sector) {
    printerSelect.innerHTML = '';
    const filtered = printersData.filter(p => p.sector === sector);
    filtered.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.ip;
        opt.textContent = `${p.name} (${p.ip})`;
        opt.dataset.dpi = p.dpi;
        opt.dataset.language = p.language || 'ZPL';
        printerSelect.appendChild(opt);
    });
    updatePrinterStatus();
    if (pollingInterval) clearInterval(pollingInterval);
    pollingInterval = setInterval(updatePrinterStatus, 3000);
}

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
    return result;
}

function displayEditSection() {
    if (currentData.length === 0) return;
    orderClient.innerHTML = `<i data-lucide="user"></i> Client : ${currentData[0].Client || 'Inconnu'}`;
    orderId.innerHTML = `<i data-lucide="file-text"></i> Commande : ${currentData[0].Commande || 'Inconnue'}`;
    
    productsTableBody.innerHTML = '';
    currentData.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="row-select large-checkbox" ${item._selected ? 'checked' : ''} oninput="updateRowData(${index}, '_selected', this.checked)"></td>
            <td><strong>${item.Libelle}</strong></td>
            <td><input type="text" value="${item.DateLivraison || item.CodeBarre17 || ''}" oninput="updateRowData(${index}, 'DateLivraison', this.value)"></td>
            <td><input type="text" value="${item.Numlot || ''}" oninput="updateRowData(${index}, 'Numlot', this.value)"></td>
            <td><input type="number" value="${item.Quantite || 0}" oninput="updateRowData(${index}, 'Quantite', this.value)"></td>
            <td><button class="btn-remove" onclick="removeLine(${index})" title="Retirer cette ligne"><i data-lucide="trash-2"></i></button></td>
        `;
        productsTableBody.appendChild(tr);
    });
    
    lucide.createIcons();
    
    uploadSection.style.display = 'none';
    editSection.style.display = 'block';
    editSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

window.updateRowData = (index, field, value) => {
    if (field === 'Quantite') value = parseInt(value) || 0;
    if (currentData[index]) currentData[index][field] = value;
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
        const response = await fetch('/print-json', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                printer_ip: printerSelect.value,
                printer_dpi: parseInt(printerSelect.options[printerSelect.selectedIndex].dataset.dpi),
                printer_language: printerSelect.options[printerSelect.selectedIndex].dataset.language,
                items: updatedData
            })
        });

        const result = await response.json();
        if (response.ok) {
            addLog(`Succès: ${result.message}`, "success");
            progressFill.style.width = '100%';
            progressText.textContent = 'Impression envoyée avec succès ! Vous pouvez regarder l\'imprimante.';
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
                isPrinting = false;
            }, 4000);
        } else {
            isPrinting = false;
            Modal.error("Erreur d'impression", result.detail);
            progressContainer.style.display = 'none';
        }
    } catch (e) {
        isPrinting = false;
        Modal.error("Problème réseau", e.message);
        progressContainer.style.display = 'none';
    }
}

stopBtn.onclick = async () => {
    const ok = await Modal.confirm("ARRÊT D'URGENCE", "Êtes-vous sûr de vouloir bloquer l'impression en cours ?", 'alert-octagon', 'icon-error');
    if (ok) {
        try {
            await fetch('/stop-print', { method: 'POST' });
            addLog("STOP envoyé. L'imprimante s'arrêtera après l'étiquette en cours.", "warning");
            progressText.textContent = 'ARRÊT DEMANDÉ...';
            progressFill.style.background = 'var(--error)';
        } catch (e) {
            addLog("Impossible d'envoyer le STOP", "error");
        }
    }
};

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
