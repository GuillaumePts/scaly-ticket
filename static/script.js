class ModalManager {
    constructor() {
        this.overlay = document.getElementById('custom-modal');
        this.titleEl = document.getElementById('modal-title');
        this.messageEl = document.getElementById('modal-message');
        this.iconEl = document.getElementById('modal-icon');
        this.confirmBtn = document.getElementById('modal-confirm');
        this.cancelBtn = document.getElementById('modal-cancel');
    }

    show(title, message, icon = 'ℹ️', showCancel = false) {
        return new Promise((resolve) => {
            this.titleEl.textContent = title;
            this.messageEl.textContent = message;
            this.iconEl.textContent = icon;
            this.overlay.style.display = 'flex';
            this.cancelBtn.style.display = showCancel ? 'block' : 'none';

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

    alert(title, message, icon = 'ℹ️') {
        return this.show(title, message, icon, false);
    }

    error(title, message) {
        return this.show(title, message, '❌', false);
    }

    confirm(title, message, icon = '❓') {
        return this.show(title, message, icon, true);
    }

    close() {
        this.overlay.style.display = 'none';
    }
}

const Modal = new ModalManager();

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const printerSelect = document.getElementById('printer');
const printerStatus = document.getElementById('printer-status');
const logs = document.getElementById('logs');
const progressContainer = document.getElementById('progress-container');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');

const sectorBtns = document.querySelectorAll('.sector-btn');
const printerSection = document.getElementById('printer-section');
const uploadSection = document.getElementById('upload-section');
const parfumSection = document.getElementById('parfum-section');
const printFormatSelect = document.getElementById('print-format');

const editSection = document.getElementById('edit-section');
const productsTableBody = document.querySelector('#products-table tbody');
const selectAllCheckbox = document.getElementById('select-all');
const orderClient = document.getElementById('order-client');
const orderId = document.getElementById('order-id');
const printBtn = document.getElementById('print-btn');
const printAllBtn = document.getElementById('print-all-btn');
const deleteSelectedBtn = document.getElementById('delete-selected-btn');
const cancelBtn = document.getElementById('cancel-btn');
const stopBtn = document.getElementById('stop-btn');

let currentData = [];
let pollingInterval = null;
let isPrinterReady = false;
let isPrinting = false;

// Gestion des secteurs
sectorBtns.forEach(btn => {
    btn.onclick = () => {
        const sector = btn.dataset.sector;
        sectorBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        fileInput.value = '';
        currentData = [];
        editSection.style.display = 'none';
        progressContainer.style.display = 'none';
        
        filterPrinters(sector);
        printerSection.style.display = 'flex';
        
        // Par défaut, on remet le format à 3up et on affiche uploadSection
        printFormatSelect.value = '3up';
        uploadSection.style.display = 'block';
        parfumSection.style.display = 'none';
        
        addLog(`Secteur changé : ${btn.textContent.trim()}`);
    };
});

// Gestion du changement de format
printFormatSelect.addEventListener('change', () => {
    if (printFormatSelect.value === '3up') {
        uploadSection.style.display = 'block';
        parfumSection.style.display = 'none';
    } else {
        uploadSection.style.display = 'none';
        parfumSection.style.display = 'block';
    }
});

// Chargement des parfums 4-up
const parfumSelect = document.getElementById('parfum-select');
const parfumPreviewImg = document.getElementById('parfum-preview-img');

parfumSelect.addEventListener('change', () => {
    if (parfumSelect.value) {
        // Ajout d'un paramètre temporel pour éviter le cache navigateur si l'image change
        parfumPreviewImg.src = `/api/preview-4up/${parfumSelect.value}?t=${new Date().getTime()}`;
        parfumPreviewImg.style.display = 'inline-block';
    } else {
        parfumPreviewImg.style.display = 'none';
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
        // Déclencher le changement pour charger la première image
        if (parfums.length > 0) {
            parfumSelect.dispatchEvent(new Event('change'));
        }
    })
    .catch(err => {
        parfumSelect.innerHTML = '<option value="">Erreur chargement</option>';
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
        toggleAddParfumBtn.textContent = '❌ Annuler';
    } else {
        addParfumForm.style.display = 'none';
        toggleAddParfumBtn.textContent = '➕ Nouveau';
    }
};

previewNewParfumBtn.onclick = () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    
    if (!nom || !ean) {
        Modal.error("Champs manquants", "Veuillez renseigner le nom et l'EAN-13.");
        return;
    }
    
    if (ean.length < 13) {
        Modal.error("EAN invalide", "L'EAN doit contenir 13 ou 14 chiffres.");
        return;
    }
    
    parfumPreviewImg.src = `/api/preview-4up-live?nom=${encodeURIComponent(nom)}&ean13=${encodeURIComponent(ean)}&t=${new Date().getTime()}`;
    parfumPreviewImg.style.display = 'inline-block';
};

saveNewParfumBtn.onclick = async () => {
    const nom = newParfumNom.value.trim();
    const ean = newParfumEan.value.trim();
    
    if (!nom || !ean) {
        Modal.error("Champs manquants", "Veuillez renseigner le nom et l'EAN-13.");
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
            Modal.alert("Succès", result.message, '✅');
            
            // Ajouter à la liste déroulante et sélectionner
            const opt = document.createElement('option');
            opt.value = result.parfum.id;
            opt.textContent = `${result.parfum.nom}`;
            parfumSelect.appendChild(opt);
            parfumSelect.value = result.parfum.id;
            
            // Fermer le formulaire
            addParfumForm.style.display = 'none';
            toggleAddParfumBtn.textContent = '➕ Nouveau';
            
            // Mettre à jour l'aperçu
            parfumSelect.dispatchEvent(new Event('change'));
        } else {
            Modal.error("Erreur serveur", result.detail);
        }
    } catch (e) {
        Modal.error("Erreur réseau", e.message);
    }
};

// Bouton impression 4-up
const print4UpBtn = document.getElementById('print-4up-btn');
const parfumQtyInput = document.getElementById('parfum-qty');

if (print4UpBtn) {
    print4UpBtn.onclick = async () => {
        if (!isPrinterReady) {
            Modal.error("Imprimante non prête", "L'imprimante n'est pas prête ou hors ligne.");
            return;
        }

        const qty = parseInt(parfumQtyInput.value);
        if (isNaN(qty) || qty <= 0) {
            Modal.error("Quantité invalide", "Veuillez saisir une quantité supérieure à 0.");
            return;
        }

        const parfumId = parfumSelect.value;
        if (!parfumId) {
            Modal.error("Parfum invalide", "Veuillez sélectionner un parfum.");
            return;
        }

        const parfumName = parfumSelect.options[parfumSelect.selectedIndex].text;
        const ok = await Modal.confirm("Impression 4-up", `Lancer l'impression de ${qty} étiquettes pour : ${parfumName} ?`, '🏭');
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
                Modal.alert("Terminé", result.message, '✅');
            } else {
                Modal.error("Erreur serveur", result.detail);
            }
        } catch (e) {
            Modal.error("Erreur réseau", e.message);
        }
    };
}

// Gestion des imprimantes
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
    localPrinters.push({ name: "Nouvelle", ip: "0.0.0.0", dpi: 203, language: "ZPL", sector: "commande", port: 9100 });
    renderManageTable();
};

savePrintersBtn.onclick = async () => {
    const ok = await Modal.confirm("Sauvegarde", "Enregistrer la nouvelle configuration des imprimantes ?", '💾');
    if (!ok) return;

    try {
        const response = await fetch('/api/printers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(localPrinters)
        });
        if (response.ok) {
            Modal.alert("Sauvegardé", "La configuration a été mise à jour. Veuillez rafraîchir la page.", '✅');
            location.reload();
        } else {
            Modal.error("Erreur", "Impossible de sauvegarder la configuration.");
        }
    } catch (e) {
        Modal.error("Erreur réseau", e.message);
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
                <select onchange="localPrinters[${index}].language = this.value">
                    <option value="ZPL" ${p.language === 'ZPL' ? 'selected' : ''}>ZPL (Zebra)</option>
                    <option value="TPCL" ${p.language === 'TPCL' ? 'selected' : ''}>TPCL (Toshiba)</option>
                </select>
            </td>
            <td>
                <select onchange="localPrinters[${index}].sector = this.value">
                    <option value="commande" ${p.sector === 'commande' ? 'selected' : ''}>Commande</option>
                    <option value="preparation" ${p.sector === 'preparation' ? 'selected' : ''}>Préparation</option>
                    <option value="production" ${p.sector === 'production' ? 'selected' : ''}>Production</option>
                </select>
            </td>
            <td><button class="btn-remove" onclick="removePrinter(${index})">×</button></td>
        `;
        managePrintersTableBody.appendChild(tr);
    });
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
            printerStatus.textContent = 'Hors ligne';
            printerStatus.classList.add('status-error');
            isPrinterReady = false;
        } else if (status.ready) {
            printerStatus.textContent = 'Prête';
            printerStatus.classList.add('status-ready');
            isPrinterReady = true;
        } else {
            printerStatus.textContent = 'Occupée / Erreur';
            printerStatus.classList.add('status-busy');
            isPrinterReady = false;
        }
    } catch (e) {
        printerStatus.textContent = 'Erreur';
        printerStatus.classList.add('status-error');
        isPrinterReady = false;
    }
}

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
            Modal.error("Erreur de fichier", "Le fichier semble vide ou mal formé (utilisez le séparateur ';')");
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
    orderClient.textContent = `Client : ${currentData[0].Client || 'Inconnu'}`;
    orderId.textContent = `Commande : ${currentData[0].Commande || 'Inconnue'}`;
    productsTableBody.innerHTML = '';
    currentData.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="checkbox" class="row-select" ${item._selected ? 'checked' : ''} oninput="updateRowData(${index}, '_selected', this.checked)"></td>
            <td><strong>${item.Libelle}</strong></td>
            <td><input type="text" value="${item.DateLivraison || item.CodeBarre17 || ''}" oninput="updateRowData(${index}, 'DateLivraison', this.value)"></td>
            <td><input type="text" value="${item.Numlot || ''}" oninput="updateRowData(${index}, 'Numlot', this.value)"></td>
            <td><input type="number" value="${item.Quantite || 0}" oninput="updateRowData(${index}, 'Quantite', this.value)"></td>
            <td><button class="btn-remove" onclick="removeLine(${index})">×</button></td>
        `;
        productsTableBody.appendChild(tr);
    });
    uploadSection.style.display = 'none';
    editSection.style.display = 'block';
    window.scrollTo({ top: editSection.offsetTop - 20, behavior: 'smooth' });
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
    const ok = await Modal.confirm("Suppression", "Supprimer cette ligne de l'impression ?", '🗑️');
    if (ok) {
        currentData.splice(index, 1);
        if (currentData.length === 0) closeEditSection();
        else displayEditSection();
    }
};

deleteSelectedBtn.onclick = async () => {
    const selectedCount = currentData.filter(item => item._selected).length;
    if (selectedCount === 0) {
        Modal.alert("Aucune sélection", "Veuillez cocher les lignes à supprimer.");
        return;
    }

    const ok = await Modal.confirm("Suppression massive", `Supprimer les ${selectedCount} lignes sélectionnées ?`, '🗑️');
    if (ok) {
        currentData = currentData.filter(item => !item._selected);
        if (currentData.length === 0) {
            closeEditSection();
        } else {
            displayEditSection();
        }
    }
};

cancelBtn.onclick = async () => {
    if (isPrinting || currentData.length === 0) {
        closeEditSection();
        return;
    }

    const ok = await Modal.confirm("Fermer", "Annuler l'importation en cours ?", '⚠️');
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
}

printBtn.onclick = () => startPrint(false);
printAllBtn.onclick = () => startPrint(true);

async function startPrint(all = false) {
    if (!isPrinterReady) {
        Modal.error("Imprimante non prête", "L'imprimante n'est pas prête ou hors ligne.");
        return;
    }

    const updatedData = currentData.filter(item => all || item._selected);

    if (updatedData.length === 0) {
        Modal.alert("Sélection vide", "Veuillez sélectionner au moins un produit.");
        return;
    }

    const ok = await Modal.confirm("Impression", `Lancer l'impression ?`, '🖨️');
    if (!ok) return;

    isPrinting = true;
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Envoi...';

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
            progressText.textContent = 'Impression terminée !';
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
                isPrinting = false;
                // On ne ferme plus la section pour que l'utilisateur garde sa commande affichée
            }, 2000);
        } else {
            isPrinting = false;
            Modal.error("Erreur serveur", result.detail);
        }
    } catch (e) {
        isPrinting = false;
        Modal.error("Erreur réseau", e.message);
    }
}

stopBtn.onclick = async () => {
    const ok = await Modal.confirm("STOP", "Voulez-vous vraiment ARRÊTER l'impression ?", '🛑');
    if (ok) {
        try {
            await fetch('/stop-print', { method: 'POST' });
            addLog("STOP envoyé. L'imprimante s'arrêtera après l'étiquette en cours.", "warning");
        } catch (e) {
            addLog("Erreur lors de l'envoi du STOP", "error");
        }
    }
};

function addLog(message, type = "") {
    const entry = document.createElement('div');
    entry.className = `log-entry ${type ? 'log-' + type : ''}`;
    const now = new Date().toLocaleTimeString();
    entry.textContent = `[${now}] ${message}`;
    logs.prepend(entry);
}
