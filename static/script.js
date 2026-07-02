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
            printerSelect.dispatchEvent(new Event('change'));
            updatePrinterStatus();
        } else {
            Modal.error("Imprimante introuvable", "Aucune imprimante Toshiba n'est configurée pour ce secteur !");
        }
    } else if (tool.startsWith('zebra')) {
        // Sélectionne l'imprimante ZPL parmi celles du secteur
        const zebra = Array.from(printerSelect.options).find(opt => opt.dataset.language === 'ZPL');
        if (zebra) {
            printerSelect.value = zebra.value;
            printerSelect.dispatchEvent(new Event('change'));
            updatePrinterStatus();
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
            const opt = printerSelect.options[printerSelect.selectedIndex];
            const response = await fetch('/print-4up', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    printer_ip: opt.value,
                    printer_dpi: parseInt(opt.dataset.dpi),
                    printer_language: opt.dataset.language,
                    parfum_id: parfumId,
                    quantity: qty,
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
                    <option value="Gravigny" ${p.sector === 'Gravigny' ? 'selected' : ''}>Gravigny</option>
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
        opt.dataset.offsetX = p.offset_x !== undefined ? p.offset_x : (p.language === 'TPCL' ? 0 : 800);
        opt.dataset.offsetY = p.offset_y !== undefined ? p.offset_y : (p.language === 'TPCL' ? 0 : 18);
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
    
    const opt = printerSelect.options[printerSelect.selectedIndex];
    const isLigne1 = opt && opt.text.startsWith("Zebra Prépa commande") && !opt.text.includes("x2");
    
    const thQuantite = document.getElementById('th-quantite');
    const thQuantitePots = document.getElementById('th-quantite-pots');
    
    if (isLigne1) {
        thQuantite.innerHTML = '<i data-lucide="box"></i> Qte Carton (300dpi)';
        thQuantite.style.backgroundColor = '#e0e7ff';
        thQuantite.style.color = '#3730a3';
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
        let extraCol = isLigne1 ? `<td style="background-color: #f0fdf4;"><input type="number" value="${item.QuantitePots || 0}" style="background-color: #dcfce7; border-color: #bbf7d0; font-weight: bold; color: #166534;" oninput="updateRowData(${index}, 'QuantitePots', this.value)"></td>` : '<td style="display:none;"></td>';
        
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="row-select large-checkbox" ${item._selected ? 'checked' : ''} oninput="updateRowData(${index}, '_selected', this.checked)"></td>
            <td><strong>${item.Libelle}</strong></td>
            <td><input type="text" value="${item.DateLivraison || item.CodeBarre17 || ''}" oninput="updateRowData(${index}, 'DateLivraison', this.value)"></td>
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

window.updateRowData = (index, field, value) => {
    if (field === 'Quantite' || field === 'QuantitePots') value = parseInt(value) || 0;
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
        const opt = printerSelect.options[printerSelect.selectedIndex];
        const isLigne1 = opt && opt.text.startsWith("Zebra Prépa commande") && !opt.text.includes("x2");
        
        let payloads = [];
        
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
        
        if (isLigne1) {
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
