/* Profils Ligne 1 : édition locale, les aperçus ne contactent aucune imprimante. */
(() => {
    const byId = id => document.getElementById(id);
    const manager = byId('ligne1-profiles-modal');
    let profiles = [];
    let scope = null;
    let selected = null;
    let productIndex = null;
    let productProfile = null;
    let blockedCategories = new Set();
    let sequence = 0;
    let timer = null;
    let latestDraft = null;
    const urls = new Map();
    const categoryTimers = new Map();
    const categorySequences = new Map();
    const categories = ['ENTIER', 'GELIFIE', 'PARAFFINÉ', 'BRASSE', 'MAIGRE', 'DESSERT', 'FF'];
    const canonicalCategory = category => String(category || '').trim().toUpperCase() === 'PARRAFINE' ? 'PARAFFINÉ' : String(category || '').trim().toUpperCase();
    const defaultRule = category => ({ category, template_300: '${description}', template_203: '${description}', enabled: true });
    const identity = item => ({ CustomerId: item.CustomerId || '', CustomerNumber: item.CustomerNumber || '', Client: item.Client || '' });
    const flavourWords = ['vanille', 'abricot', 'fraise', 'framboise', 'myrtille', 'nature', 'citron', 'amande', 'chocolat', 'caramel', 'café', 'figue', 'poire', 'cerise', 'noisette', 'miel', 'pêche', 'marron', 'mandarine', 'griotte', 'litchi'];

    function templateValues(item) {
        return {
            parfum: item.Parfum || '',
            description: item.ItemDescription || item.Libelle || '',
            description_2: item.ItemDescription2 || '',
            categorie: item.ItemCategoryCode || '',
            unite: item.UnitOfMeasureCode || '',
            client: item.Client || '',
            quantite: item.QuantiteCartons ?? item.Quantite ?? '',
            poids: item.ItemWeightGrams || ''
        };
    }

    function showTemplate(template, item) {
        const values = templateValues(item);
        return String(template || '').replace(/\$\{([^{}]+)\}/g, (_token, name) => String(values[name] ?? ''));
    }

    function replaceWholeValue(text, value, replacement) {
        const escaped = String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const matcher = new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}(?=$|[^\\p{L}\\p{N}])`, 'giu');
        return text.replace(matcher, (_match, prefix) => `${prefix}${replacement}`);
    }

    function saveTemplate(displayText, item, extraFlavours = []) {
        let template = String(displayText || '').trim();
        const flavours = [...new Set([...extraFlavours, item.Parfum || '', ...flavourWords].filter(Boolean))]
            .sort((a, b) => String(b).length - String(a).length);
        flavours.forEach(flavour => { template = replaceWholeValue(template, flavour, '${parfum}'); });
        return template;
    }

    function templateFromInput(input, sourceTemplate, sample, extraFlavours = []) {
        if (input.value === input.dataset.displayTemplate) {
            // Corrige aussi les anciennes règles qui avaient enregistré un
            // parfum en clair, même si l'opérateur ne touche pas au texte.
            return saveTemplate(sourceTemplate, sample, extraFlavours);
        }
        return saveTemplate(input.value, sample, extraFlavours);
    }

    function readableWarnings(warnings = []) {
        const names = { parfum: 'parfum', description: 'description', description_2: 'seconde description', categorie: 'catégorie d’article', unite: 'unité', client: 'client', quantite: 'quantité', poids: 'poids' };
        return warnings.map(warning => warning.replace(/\$\{([^}]+)\}/g, (_token, key) => names[key] || 'information')).join(' · ');
    }

    // Sortir l'overlay de la page pour éviter les contextes de positionnement
    // créés par les animations du portail.
    document.body.appendChild(apiOrderLabelPreviewModal);

    async function api(path, body, method = 'POST') {
        const options = body === undefined
            ? (method === 'POST' ? {} : { method })
            : { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
        const response = await fetch('/api/ligne1/' + path, options);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Impossible de charger les profils.');
        return data;
    }

    async function reload() {
        const data = await api('profiles');
        profiles = data.profiles;
        scope = data.scope;
        return data;
    }

    async function refresh() {
        if (!currentData.length || !currentData[0].BCScope) return;
        const temporaryDays = currentData[0].ClientMinDlcDaysTransient
            ? Number(currentData[0].ClientMinDlcDays)
            : undefined;
        const data = await api('resolve', { items: currentData, min_dlc_days: temporaryDays });
        currentData = data.items;
    }

    function showStatus() {
        const status = byId('ligne1-client-status');
        const item = currentData[0];
        const enabled = currentSector === 'prepa_commande' && currentDataSource === 'business-central' && item?.BCScope;
        status.hidden = !enabled;
        if (!enabled) return;
        const message = !item.ClientProfileId ? 'Client non configuré · descriptions BC par défaut'
            : !item.ClientProfileActive ? 'Profil désactivé · descriptions BC par défaut'
            : 'Profil client actif · libellés par catégorie';
        status.replaceChildren();
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'api-preview-product';
        button.textContent = item.Client;
        button.onclick = () => openManager(item.ClientProfileId);
        const text = document.createElement('span');
        text.textContent = message;
        status.append(button, text);
        const warnings = [...new Set([
            ...currentData.flatMap(row => row.LabelWarnings || []),
            ...currentData.map(row => row.LotSelectionWarning).filter(Boolean),
            ...currentData.map(row => row.LotShortageWarning).filter(Boolean),
            ...currentData.map(row => row.CartonLabelWarning).filter(Boolean),
        ])];
        if (warnings.length) {
            const note = document.createElement('small');
            note.className = 'ligne1-warning'; note.textContent = readableWarnings(warnings);
            status.append(note);
        }
    }

    function requestMinimumDlcDays() {
        const overlay = byId('ligne1-min-dlc-days-modal');
        const form = byId('ligne1-min-dlc-days-form');
        const input = byId('ligne1-min-dlc-days-input');
        const cancel = byId('ligne1-min-dlc-days-cancel');
        input.value = '';
        overlay.style.display = 'flex';
        input.focus();
        return new Promise(resolve => {
            const finish = value => {
                overlay.style.display = 'none';
                form.onsubmit = null;
                cancel.onclick = null;
                overlay.onclick = null;
                document.removeEventListener('keydown', onKeyDown);
                resolve(value);
            };
            const onKeyDown = event => { if (event.key === 'Escape') finish(null); };
            form.onsubmit = event => {
                event.preventDefault();
                if (!form.reportValidity()) return;
                finish(Number(input.value));
            };
            cancel.onclick = () => finish(null);
            overlay.onclick = event => { if (event.target === overlay) finish(null); };
            document.addEventListener('keydown', onKeyDown);
        });
    }

    async function createImportedProfile(minDlcDays) {
        const first = currentData[0];
        const profile = await api('profiles', { identity: identity(first), categories: currentData.map(i => i.ItemCategoryCode).filter(Boolean), min_dlc_days: minDlcDays });
        await refresh();
        return profile;
    }

    async function saveImportedProfileDays(profile, minDlcDays) {
        await api(`profiles/${profile.id}`, {
            revision: profile.revision,
            display_name: profile.display_name,
            active: profile.active,
            rules: profile.rules,
            blocked_categories: profile.blocked_categories || [],
            min_dlc_days: minDlcDays,
        }, 'PUT');
        await refresh();
    }

    async function onImport() {
        await refresh();
        if (!currentData[0]?.ClientProfileId) {
            const yes = await Modal.confirm('Nouveau client', `Nouveau client, voulez-vous ajouter ce client ?\n${currentData[0].Client}`, 'user-plus');
            const minDlcDays = await requestMinimumDlcDays();
            if (minDlcDays === null) return false;
            if (yes) {
                await createImportedProfile(minDlcDays);
            } else {
                currentData.forEach(item => {
                    item.ClientMinDlcDays = minDlcDays;
                    item.ClientMinDlcDaysTransient = true;
                });
                await refresh();
                addLog('Délai appliqué uniquement à cette commande ; aucun profil client n’a été enregistré.', 'warning');
            }
            return true;
        }
        if (currentData[0].ClientMinDlcDays === null || currentData[0].ClientMinDlcDays === undefined) {
            await reload();
            const profile = profiles.find(entry => entry.id === currentData[0].ClientProfileId);
            if (!profile) return false;
            const minDlcDays = await requestMinimumDlcDays();
            if (minDlcDays === null) return false;
            await saveImportedProfileDays(profile, minDlcDays);
        }
        return true;
    }

    async function imagePreview(dpi, ticket, image, isCurrent) {
        const printer = dpi === 300 ? printerSelect.options[printerSelect.selectedIndex] : null;
        const styling = {};
        ['title', 'gs1', 'lot'].forEach(name => {
            styling[`${name}_size`] = Number(printer?.dataset[`${name}Size`]) || 0;
            styling[`${name}_bold`] = printer?.dataset[`${name}Bold`] === 'true';
        });
        const response = await fetch(`/api/commande/preview/${dpi}`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ticket, ...styling })
        });
        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.detail || 'Aperçu indisponible');
        }
        const blob = await response.blob();
        if (!isCurrent()) return;
        const url = URL.createObjectURL(blob);
        const candidate = new Image(); candidate.src = url;
        try { await candidate.decode(); }
        catch (error) { URL.revokeObjectURL(url); throw error; }
        if (!isCurrent()) { URL.revokeObjectURL(url); return; }
        if (urls.has(image)) URL.revokeObjectURL(urls.get(image));
        urls.set(image, url);
        image.src = url;
        image.style.display = 'block';
    }

    async function updateProductPreview() {
        const seq = ++sequence;
        latestDraft = null;
        byId('ligne1-save-product-rule').disabled = true;
        const item = currentData[productIndex];
        if (!item || apiOrderLabelPreviewModal.style.display === 'none') return;
        const rule = { category: item.ItemCategoryCode || '', template_300: byId('ligne1-template-300').value, template_203: byId('ligne1-template-203').value };
        const frameImages = [203, 300].map(dpi => byId(`api-order-label-preview-${dpi}`));
        frameImages.forEach(img => img.classList.add('ligne1-image-loading'));
        try {
            const data = await api('resolve', { items: [item], draft: rule, draft_flavour: byId('ligne1-flavour').value });
            if (seq !== sequence) return;
            const resolved = data.items[0];
            byId('ligne1-variable-values').textContent = `Produit : ${resolved.ItemDescription || resolved.Libelle} · Unité de vente : ${resolved.UnitOfMeasureCode || '—'} · Nombre de cartons : ${resolved.QuantiteCartons ?? resolved.Quantite}`;
            byId('ligne1-editor-warnings').textContent = readableWarnings(resolved.LabelWarnings || []);
            const results = await Promise.allSettled([203, 300].map(async dpi => {
                const loading = byId(`api-order-label-preview-${dpi}-loading`);
                loading.textContent = 'Actualisation…'; loading.style.display = 'inline';
                try {
                    await imagePreview(dpi, resolved, byId(`api-order-label-preview-${dpi}`), () => seq === sequence);
                    if (seq === sequence) loading.style.display = 'none';
                } catch (error) {
                    if (seq === sequence) loading.textContent = error.message;
                    throw error;
                }
            }));
            if (seq !== sequence) return;
            if (results.every(r => r.status === 'fulfilled')) latestDraft = resolved;
            byId('ligne1-save-product-rule').disabled = !latestDraft || !item.ItemCategoryCode || !productProfile || !productProfile.active;
        } catch (error) {
            if (seq === sequence) byId('ligne1-editor-warnings').textContent = error.message;
        } finally {
            if (seq === sequence) frameImages.forEach(img => img.classList.remove('ligne1-image-loading'));
        }
    }

    function scheduleProductPreview() {
        sequence += 1; // invalider aussi pendant le délai de debounce
        latestDraft = null;
        byId('ligne1-save-product-rule').disabled = true;
        [203, 300].forEach(dpi => byId(`api-order-label-preview-${dpi}`).classList.add('ligne1-image-loading'));
        clearTimeout(timer);
        timer = setTimeout(updateProductPreview, 220);
    }

    async function openProduct(index) {
        productIndex = index;
        productProfile = null;
        sequence += 1;
        try {
            await reload();
            const item = currentData[index];
            if (!item) return;
            productProfile = profiles.find(p => p.id === item.ClientProfileId) || null;
            byId('ligne1-product-editor').hidden = false;
            byId('ligne1-save-product-rule').hidden = false;
            byId('api-order-label-preview-title').textContent = item.Libelle;
            byId('api-order-label-preview-meta').textContent = `Unité : ${item.UnitOfMeasureCode || '—'} · EAN14 : ${item.CodeBarre01 || '—'} · GENCOD : ${item.GENCOD || '—'}`;
            byId('ligne1-editor-category').textContent = `Client : ${item.Client} · Catégorie : ${item.ItemCategoryCode || 'absente'}${!productProfile ? ' · Ajoutez le profil du client pour enregistrer.' : !productProfile.active ? ' · Activez le profil pour enregistrer.' : ''}`;
            const rule = productProfile?.active ? productProfile.rules.find(r => r.category === item.ItemCategoryCode && r.enabled) : null;
            const template300 = byId('ligne1-template-300');
            const template203 = byId('ligne1-template-203');
            template300.value = item.Libelle300 || item.ItemDescription || item.Libelle || '';
            template203.value = item.Libelle203 || item.ItemDescription || item.Libelle || '';
            template300.dataset.displayTemplate = template300.value;
            template203.dataset.displayTemplate = template203.value;
            template300.dataset.sourceTemplate = rule?.template_300 || '${description}';
            template203.dataset.sourceTemplate = rule?.template_203 || '${description}';
            byId('ligne1-flavour').value = item.Parfum || '';
            byId('ligne1-rgf-suggestion').hidden = item.ItemCategoryCode !== 'ENTIER' || !/CREM(CENTRE|LOG)/i.test(item.Client);
            [203, 300].forEach(dpi => { byId(`api-order-label-preview-${dpi}`).style.display = 'none'; });
            apiOrderLabelPreviewModal.style.display = 'flex';
            await updateProductPreview();
        } catch (error) { Modal.error('Profils clients', error.message); }
    }

    byId('ligne1-rgf-suggestion').onclick = () => {
        const flavour = byId('ligne1-flavour').value.trim();
        byId('ligne1-template-300').value = `6 Yaourt entier ${flavour} RGF - 2X125G`;
        byId('ligne1-template-203').value = `RGF ${flavour} 2X125gr`;
        scheduleProductPreview();
    };
    ['ligne1-template-300', 'ligne1-template-203', 'ligne1-flavour'].forEach(id => byId(id).addEventListener('input', scheduleProductPreview));
    byId('ligne1-save-product-rule').onclick = async () => {
        clearTimeout(timer);
        const item = currentData[productIndex];
        if (!latestDraft || !productProfile || !item?.ItemCategoryCode) return;
        const button = byId('ligne1-save-product-rule'); button.disabled = true;
        try {
            const rules = productProfile.rules.filter(r => r.category !== item.ItemCategoryCode);
            const flavours = currentData.filter(row => row.ItemCategoryCode === item.ItemCategoryCode).map(row => row.Parfum);
            rules.push({ category: item.ItemCategoryCode,
                template_300: templateFromInput(byId('ligne1-template-300'), byId('ligne1-template-300').dataset.sourceTemplate, item, flavours),
                template_203: templateFromInput(byId('ligne1-template-203'), byId('ligne1-template-203').dataset.sourceTemplate, item, flavours), enabled: true });
            await api(`profiles/${productProfile.id}`, {
                revision: productProfile.revision, display_name: productProfile.display_name, active: productProfile.active,
                identity: identity(item), rules, blocked_categories: productProfile.blocked_categories || [],
                min_dlc_days: productProfile.min_dlc_days,
                flavour: { item_no: item.Item_No, value: byId('ligne1-flavour').value, revision: item.ParfumRevision || 0 }
            }, 'PUT');
            await refresh();
            closeApiOrderLabelPreview();
            displayEditSection();
            addLog('Libellés enregistrés pour ce client et cette catégorie.', 'success');
        } catch (error) { byId('ligne1-editor-warnings').textContent = error.message; }
        finally { button.disabled = false; }
    };

    function readRule(card) {
        const category = canonicalCategory(card.dataset.category);
        const sample = sampleFor(category);
        const flavours = currentData.filter(row => row.ItemCategoryCode === category).map(row => row.Parfum);
        const input300 = card.querySelector('[data-template="300"]');
        const input203 = card.querySelector('[data-template="203"]');
        return { category,
            template_300: templateFromInput(input300, input300.dataset.sourceTemplate, sample, flavours),
            template_203: templateFromInput(input203, input203.dataset.sourceTemplate, sample, flavours),
            enabled: card.querySelector('[data-rule-active]').checked };
    }

    function sampleFor(category) {
        const row = currentData.find(i => i.BCScope && i.ItemCategoryCode === category);
        if (row) return { ...row, Client: byId('ligne1-profile-name').value };
        return { Client: byId('ligne1-profile-name').value || 'Client', Commande: 'APERÇU', DateLivraison: '',
            ItemCategoryCode: category, ItemDescription: 'Produit de démonstration Fraise', ItemDescription2: 'Fraise',
            Libelle: 'Produit de démonstration Fraise', Parfum: 'Fraise', UnitOfMeasureCode: 'X2',
            Quantite: 6, QuantiteCartons: 6, CodeBarre01: '13374270040429', GENCOD: '3374270040422',
            CodeBarre17: '261231', CodeBarre10: 'LOTDEMO', Numlot: 'LOTDEMO' };
    }

    async function previewCategory(card, dpi) {
        const key = `${card.dataset.category}-${dpi}`;
        const seq = (categorySequences.get(key) || 0) + 1;
        categorySequences.set(key, seq);
        const message = card.querySelector('[data-preview-message]');
        const image = card.querySelector(`[data-preview="${dpi}"]`);
        image.hidden = false; image.classList.add('ligne1-image-loading');
        const sample = sampleFor(card.dataset.category);
        try {
            const data = await api('resolve', { items: [sample], draft: readRule(card), draft_flavour: sample.Parfum || 'Fraise' });
            await imagePreview(dpi, data.items[0], image, () => manager.style.display !== 'none' && card.isConnected && categorySequences.get(key) === seq);
            if (categorySequences.get(key) === seq) message.textContent = `${sample.Commande === 'APERÇU' ? 'Exemple fictif : aucun produit de cette catégorie dans la commande.' : 'Aperçu avec un produit de la commande.'} ${readableWarnings(data.items[0].LabelWarnings || [])}`;
        } catch (error) { if (categorySequences.get(key) === seq) message.textContent = error.message; }
        finally { if (categorySequences.get(key) === seq) image.classList.remove('ligne1-image-loading'); }
    }

    function addRule(rule) {
        const container = byId('ligne1-profile-rules');
        const category = canonicalCategory(rule.category);
        if ([...container.children].some(card => card.dataset.category === category)) return;
        const card = document.createElement('section'); card.className = 'ligne1-category-rule'; card.dataset.category = category;
        card.innerHTML = '<div class="ligne1-category-heading"><strong></strong><div class="ligne1-category-options"><label><input type="checkbox" data-print-enabled> Inclure à l’impression</label><label><input type="checkbox" data-rule-active> Libellé personnalisé</label></div></div><div class="ligne1-fields"><label>Texte de l’étiquette carton<input data-template="300" maxlength="500"></label><label>Texte des étiquettes pots<input data-template="203" maxlength="500"></label></div><div class="ligne1-category-previews"><button type="button" class="btn-secondary" data-dpi="300">Aperçu carton</button><button type="button" class="btn-secondary" data-dpi="203">Aperçu pots</button></div><div class="ligne1-small-previews"><img data-preview="300" hidden alt="Aperçu carton"><img data-preview="203" hidden alt="Aperçu pots"></div><p data-preview-message class="ligne1-warning"></p>';
        card.querySelector('strong').textContent = category;
        card.querySelector('[data-rule-active]').checked = !!rule.enabled;
        card.querySelector('[data-print-enabled]').checked = !blockedCategories.has(category);
        const sample = sampleFor(category);
        const input300 = card.querySelector('[data-template="300"]');
        const input203 = card.querySelector('[data-template="203"]');
        input300.value = showTemplate(rule.template_300, sample);
        input203.value = showTemplate(rule.template_203, sample);
        input300.dataset.displayTemplate = input300.value;
        input203.dataset.displayTemplate = input203.value;
        input300.dataset.sourceTemplate = rule.template_300;
        input203.dataset.sourceTemplate = rule.template_203;
        card.querySelectorAll('[data-dpi]').forEach(button => button.onclick = () => previewCategory(card, Number(button.dataset.dpi)));
        card.querySelectorAll('[data-template]').forEach(input => input.oninput = () => {
            [300, 203].forEach(dpi => {
                const key = `${card.dataset.category}-${dpi}`;
                categorySequences.set(key, (categorySequences.get(key) || 0) + 1);
                clearTimeout(categoryTimers.get(key));
                if (!card.querySelector(`[data-preview="${dpi}"]`).hidden) categoryTimers.set(key, setTimeout(() => previewCategory(card, dpi), 220));
            });
        });
        container.append(card);
    }

    function showProfileForm() {
        byId('ligne1-profile-empty').hidden = true;
        byId('ligne1-profile-form').hidden = false;
        byId('ligne1-profile-form').classList.remove('is-deleting');
    }

    function showProfileEmpty(title, message) {
        byId('ligne1-profile-form').hidden = true;
        byId('ligne1-profile-empty-title').textContent = title;
        byId('ligne1-profile-empty-message').textContent = message;
        const empty = byId('ligne1-profile-empty');
        empty.hidden = false;
        empty.classList.remove('is-entering');
        void empty.offsetWidth;
        empty.classList.add('is-entering');
        lucide.createIcons();
    }

    function fillProfile(profile) {
        selected = profile;
        byId('ligne1-profile-delete').hidden = !profile;
        if (profile) showProfileForm();
        else byId('ligne1-profile-form').hidden = true;
        blockedCategories = new Set(profile?.blocked_categories || []);
        byId('ligne1-profile-name').value = profile?.display_name || '';
        byId('ligne1-profile-number').value = profile?.customer_number || '';
        byId('ligne1-profile-bc-id').value = profile?.customer_id || '';
        byId('ligne1-profile-min-dlc-days').value = profile?.min_dlc_days ?? '';
        byId('ligne1-profile-active').checked = profile ? !!profile.active : true;
        byId('ligne1-profile-rules').replaceChildren();
        const rulesByCategory = new Map();
        (profile?.rules || categories.map(defaultRule)).forEach(rule => {
            const category = canonicalCategory(rule.category);
            const previous = rulesByCategory.get(category);
            if (!previous || rule.category === category) rulesByCategory.set(category, { ...rule, category });
        });
        [...rulesByCategory.values()].forEach(addRule);
        byId('ligne1-profile-message').textContent = '';
    }

    async function openManager(profileId) {
        try {
            await reload();
            byId('ligne1-profiles-scope').textContent = `${scope.environment} · ${scope.company}`;
            const select = byId('ligne1-profile-select'); select.replaceChildren();
            const empty = new Option('— Sélectionner un client —', ''); select.add(empty);
            profiles.forEach(profile => select.add(new Option(`${profile.display_name}${profile.active ? '' : ' (désactivé)'}`, profile.id)));
            select.value = profileId || profiles[0]?.id || '';
            fillProfile(profiles.find(p => p.id === select.value));
            if (profileId === null && currentData[0]?.BCScope) {
                select.value = ''; fillProfile(null);
                byId('ligne1-profile-name').value = currentData[0].Client;
                byId('ligne1-profile-number').value = currentData[0].CustomerNumber || '';
                byId('ligne1-profile-bc-id').value = currentData[0].CustomerId || '';
                showProfileForm();
            } else if (!select.value) {
                showProfileEmpty(profiles.length ? 'Aucun profil sélectionné' : 'Aucun profil client local',
                    profiles.length ? 'Choisissez un client dans la liste ou créez une nouvelle fiche locale.' : 'La base locale ne contient aucun profil client. Vous pouvez en créer un depuis cette fenêtre.');
            }
            manager.style.display = 'flex'; lucide.createIcons();
        } catch (error) { Modal.error('Profils clients', error.message); }
    }

    byId('ligne1-profile-select').onchange = event => {
        const profile = profiles.find(p => p.id === event.target.value);
        if (profile) fillProfile(profile);
        else {
            fillProfile(null);
            showProfileEmpty(profiles.length ? 'Aucun profil sélectionné' : 'Aucun profil client local',
                profiles.length ? 'Choisissez un client dans la liste ou créez une nouvelle fiche locale.' : 'La base locale ne contient aucun profil client. Vous pouvez en créer un depuis cette fenêtre.');
        }
    };
    const startNewProfile = () => {
        byId('ligne1-profile-select').value = ''; fillProfile(null);
        const item = currentData[0];
        if (item?.BCScope) {
            byId('ligne1-profile-name').value = item.Client || '';
            byId('ligne1-profile-number').value = item.CustomerNumber || '';
            byId('ligne1-profile-bc-id').value = item.CustomerId || '';
        }
        showProfileForm();
    };
    byId('ligne1-new-profile').onclick = startNewProfile;
    byId('ligne1-profile-empty-create').onclick = startNewProfile;
    byId('ligne1-add-category').onclick = () => {
        const input = byId('ligne1-new-category');
        const category = input.value.trim().toUpperCase();
        if (category) { addRule(defaultRule(category)); input.value = ''; }
    };
    byId('ligne1-profile-form').onsubmit = async event => {
        event.preventDefault();
        const save = byId('ligne1-profile-save'); save.disabled = true;
        try {
            const rules = [...byId('ligne1-profile-rules').children].map(readRule);
            const clientIdentity = { Client: byId('ligne1-profile-name').value, CustomerNumber: byId('ligne1-profile-number').value, CustomerId: byId('ligne1-profile-bc-id').value };
            const minDlcDays = Number(byId('ligne1-profile-min-dlc-days').value);
            // Une transaction unique : aucun profil partiellement créé.
            const active = byId('ligne1-profile-active').checked;
            const blocked = [...byId('ligne1-profile-rules').children]
                .filter(card => !card.querySelector('[data-print-enabled]').checked)
                .map(card => card.dataset.category);
            selected = selected
                ? await api(`profiles/${selected.id}`, { revision: selected.revision, display_name: clientIdentity.Client,
                    active, rules, blocked_categories: blocked, min_dlc_days: minDlcDays }, 'PUT')
                : await api('profiles', { identity: clientIdentity, active, rules, blocked_categories: blocked, min_dlc_days: minDlcDays });
            await refresh(); displayEditSection(); closeManager();
        } catch (error) { byId('ligne1-profile-message').textContent = error.message; }
        finally { save.disabled = false; }
    };
    byId('ligne1-profile-delete').onclick = async () => {
        if (!selected) return;
        const profileToDelete = selected;
        const confirmed = await Modal.confirm(
            'Supprimer ce profil local ?',
            `Le profil « ${profileToDelete.display_name} » et ses réglages seront supprimés de la base locale. Cette action ne modifie rien dans Business Central.`,
            'trash-2', 'icon-error'
        );
        if (!confirmed) return;

        const button = byId('ligne1-profile-delete');
        const form = byId('ligne1-profile-form');
        const label = [...button.childNodes].find(node => node.nodeType === Node.TEXT_NODE);
        if (label) label.textContent = ' Suppression en cours…';
        button.disabled = true;
        button.setAttribute('aria-busy', 'true');
        form.classList.add('is-deleting');
        lucide.createIcons();
        let deletionSucceeded = false;
        try {
            if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
                await new Promise(resolve => setTimeout(resolve, 220));
            }
            await api(`profiles/${encodeURIComponent(profileToDelete.id)}?revision=${profileToDelete.revision}`, undefined, 'DELETE');
            deletionSucceeded = true;
            byId('ligne1-profile-select').value = '';
            fillProfile(null);
            showProfileEmpty('Profil supprimé', profiles.length > 1
                ? 'La fiche a été supprimée de la base locale. Choisissez un autre client ou créez un nouveau profil.'
                : 'La fiche a été supprimée. Il n’y a maintenant plus aucun client dans la base locale.');
            await reload();
            const select = byId('ligne1-profile-select');
            select.replaceChildren(new Option('— Sélectionner un client —', ''));
            profiles.forEach(profile => select.add(new Option(`${profile.display_name}${profile.active ? '' : ' (désactivé)'}`, profile.id)));
            select.value = '';
            fillProfile(null);
            showProfileEmpty(profiles.length ? 'Profil supprimé' : 'Aucun profil client local', profiles.length
                ? 'La fiche a été supprimée de la base locale. Choisissez un autre client dans la liste ou créez un nouveau profil.'
                : 'La fiche a été supprimée. Il n’y a maintenant plus aucun client dans la base locale.');

            if (currentData.length && currentData[0]?.BCScope) {
                try {
                    await refresh();
                    displayEditSection();
                } catch (refreshError) {
                    byId('ligne1-profile-message').textContent = `Profil supprimé. La commande affichée n’a pas pu être actualisée : ${refreshError.message}`;
                }
            }
        } catch (error) {
            if (deletionSucceeded) {
                showProfileEmpty('Profil supprimé', `La fiche a bien été supprimée, mais la liste n’a pas pu être actualisée : ${error.message}`);
            } else {
                byId('ligne1-profile-message').textContent = error.message;
                form.classList.remove('is-deleting');
                showProfileForm();
            }
        } finally {
            button.disabled = false;
            button.removeAttribute('aria-busy');
            if (label) label.textContent = ' Supprimer ce profil local';
            lucide.createIcons();
        }
    };
    function closeManager() {
        manager.style.display = 'none';
        categorySequences.clear();
        categoryTimers.forEach(clearTimeout); categoryTimers.clear();
        urls.forEach((url, image) => { if (manager.contains(image)) { URL.revokeObjectURL(url); urls.delete(image); } });
    }
    byId('ligne1-profiles-close').onclick = closeManager;
    byId('ligne1-profile-cancel').onclick = closeManager;
    manager.onclick = event => { if (event.target === manager) closeManager(); };
    document.querySelectorAll('[data-open-client-profiles]').forEach(button => button.onclick = () => openManager());
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape') { closeManager(); closeApiOrderLabelPreview(); }
    });
    const previousClose = closeApiOrderLabelPreview;
    closeApiOrderLabelPreview = function () {
        sequence += 1; clearTimeout(timer); latestDraft = null;
        urls.forEach((url, image) => { if (apiOrderLabelPreviewModal.contains(image)) { URL.revokeObjectURL(url); urls.delete(image); } });
        previousClose();
    };
    apiOrderLabelPreviewClose.onclick = closeApiOrderLabelPreview;
    apiOrderLabelPreviewCloseBottom.onclick = closeApiOrderLabelPreview;
    window.Ligne1Profiles = { onImport, refresh, showStatus, openProduct, openManager };
})();
