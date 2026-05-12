// ==============================================================================
// CK ATS V1 - SCRIPT.JS - VERSÃO MODULARIZADA E LIMPA
// Design Responsivo e Padrão Sênior
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log("CK ATS V1 script.js carregado e em execução.");

    // ==========================================================================
    // 1. LÓGICA UNIVERSAL (Executa em todas as páginas)
    // ==========================================================================
    const userNomeSpan = document.getElementById('user-nome');
    if (userNomeSpan) {
        const nomeUsuario = localStorage.getItem('user_nome');
        if (nomeUsuario) {
            userNomeSpan.textContent = `Olá, ${nomeUsuario}!`;
        }
    }

    // ==========================================================================
    // 2. LÓGICA DA PÁGINA DE VAGAS (vagas.html)
    // ==========================================================================
    const jobListContainer = document.getElementById('jobList');
    if (jobListContainer) {
        const modal = document.getElementById('modalNovaVaga');
        const btnOpenModal = document.getElementById('btnCriarNovaVaga');
        const btnCloseModal = document.getElementById('closeModalNovaVaga');
        const form = document.getElementById('formNovaVaga');
        const vagaNomeInput = document.getElementById('vagaNome');
        const vagaRequisitosTextarea = document.getElementById('vagaRequisitos');
        const btnSugerirHabilidades = document.getElementById('btnSugerirHabilidades');
        const tagsContainer = document.getElementById('tagsContainer');
        const manualSkillInput = document.getElementById('manualSkillInput');
        const btnCancelModal = document.getElementById('btnCancelModal');

        function adicionarTag(habilidade) {
            if (!habilidade || habilidade.trim() === '') return;
            const tag = document.createElement('div');
            tag.className = 'skill-tag-editavel';
            tag.innerHTML = `<span class="skill-tag">${habilidade.trim()}</span><span class="remover-tag" style="cursor:pointer; margin-left:8px; color:var(--danger-color);">&times;</span>`;
            tag.querySelector('.remover-tag').onclick = () => tag.remove();
            if (tagsContainer) tagsContainer.appendChild(tag);
        }

        async function renderVagas() {
            jobListContainer.innerHTML = '<p>Carregando vagas...</p>';
            try {
                const res = await fetch('/api/vagas');
                if (!res.ok) throw new Error('Falha ao buscar vagas do servidor.');
                
                const data = await res.json();
                jobListContainer.innerHTML = ''; 

                if (data.success && data.vagas.length > 0) {
                    data.vagas.forEach(vaga => {
                        const vagaCard = document.createElement('div');
                        vagaCard.className = 'card vaga-card'; // Usando a classe card do main.css
                        vagaCard.id = `vaga-${vaga.id}`;

                        const habilidadesHTML = vaga.habilidades_chave.map(h => `<span class="skill-tag">${h}</span>`).join(' ');
                        const descricaoCompleta = vaga.requisitos;
                        const ehLongo = descricaoCompleta.length > 150;
                        const descricaoVisivel = ehLongo ? descricaoCompleta.substring(0, 150) + '...' : descricaoCompleta;

                        vagaCard.innerHTML = `
                            <div class="vaga-header" style="display:flex; justify-content:space-between; margin-bottom: 1rem;">
                                <h3>${vaga.nome}</h3>
                                <small style="color: var(--text-muted);">Criada em: ${vaga.data_criacao || 'N/A'}</small>
                            </div>
                            <div class="vaga-body" style="margin-bottom: 1.5rem;">
                                <p class="vaga-descricao" style="white-space: pre-line;">${descricaoVisivel}</p>
                                ${ehLongo ? `<a href="#" class="toggle-details-btn" data-fulltext="${encodeURIComponent(descricaoCompleta)}" style="color: var(--secondary-color); text-decoration: none; font-weight: 600;">Ver mais...</a>` : ''}
                            </div>
                            <div class="vaga-footer" style="display:flex; justify-content:space-between; align-items:flex-end;">
                                <div class="skill-tags">${habilidadesHTML || '<span style="color:var(--text-muted);">Nenhuma habilidade cadastrada.</span>'}</div>
                                <button class="btn btn-danger btn-sm btn-excluir-vaga" data-id="${vaga.id}">Excluir</button>
                            </div>
                        `;
                        jobListContainer.appendChild(vagaCard);
                    });
                } else {
                    jobListContainer.innerHTML = '<p>Nenhuma vaga ativa encontrada.</p>';
                }
            } catch (error) {
                console.error("Erro ao renderizar vagas:", error);
                jobListContainer.innerHTML = '<p style="color:var(--danger-color);">Erro ao carregar as vagas.</p>';
            }
        }

        jobListContainer.addEventListener('click', async (e) => {
            const target = e.target;
            if (target.classList.contains('btn-excluir-vaga')) {
                const vagaId = target.dataset.id;
                if (confirm('Tem certeza que deseja excluir esta vaga?')) {
                    await fetch(`/api/vagas/${vagaId}`, { method: 'DELETE' });
                    renderVagas();
                }
            }
            if (target.classList.contains('toggle-details-btn')) {
                e.preventDefault();
                const link = target;
                const descricaoP = link.previousElementSibling;
                if (link.textContent === 'Ver mais...') {
                    descricaoP.textContent = decodeURIComponent(link.dataset.fulltext);
                    link.textContent = 'Ocultar';
                } else {
                    descricaoP.textContent = decodeURIComponent(link.dataset.fulltext).substring(0, 150) + '...';
                    link.textContent = 'Ver mais...';
                }
            }
        });
        
        const openModal = () => { if (modal) modal.style.display = 'flex'; };
        const closeModal = () => { if (modal) { modal.style.display = 'none'; form.reset(); if (tagsContainer) tagsContainer.innerHTML = ''; }};
        if (btnOpenModal) btnOpenModal.onclick = openModal;
        if (btnCloseModal) btnCloseModal.onclick = closeModal;
        if (btnCancelModal) btnCancelModal.onclick = closeModal;

        if (btnSugerirHabilidades) {
            btnSugerirHabilidades.addEventListener('click', async () => {
                const descricao = vagaRequisitosTextarea.value;
                if (descricao.trim().length < 20) {
                    alert("A descrição precisa ter pelo menos 20 caracteres para a IA analisar.");
                    return;
                }
                btnSugerirHabilidades.disabled = true;
                btnSugerirHabilidades.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Analisando...';

                try {
                    const res = await fetch('/api/vagas/sugerir-habilidades', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ descricao })
                    });
                    const data = await res.json();
                    if (data.success) {
                        if (tagsContainer) tagsContainer.innerHTML = '';
                        data.habilidades.forEach(h => adicionarTag(h));
                    } else { 
                        alert('Falha ao gerar habilidades com IA.'); 
                    }
                } catch (error) {
                    console.error("Erro na API Gemini:", error);
                    alert('Erro de conexão.');
                } finally {
                    btnSugerirHabilidades.disabled = false;
                    btnSugerirHabilidades.innerHTML = '<i class="fas fa-magic"></i> Sugerir com IA';
                }
            });
        }

        if (manualSkillInput) {
            manualSkillInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    adicionarTag(manualSkillInput.value);
                    manualSkillInput.value = '';
                }
            });
        }
        
        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const nome = vagaNomeInput.value;
                const requisitos = vagaRequisitosTextarea.value;
                const habilidades_chave = tagsContainer ? Array.from(tagsContainer.querySelectorAll('span:first-child')).map(span => span.textContent) : [];
                
                const res = await fetch('/api/vagas', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ nome, requisitos, habilidades_chave })
                });
                
                if (res.ok) {
                    closeModal();
                    renderVagas();
                } else {
                    alert('Erro ao salvar a vaga.');
                }
            });
        }
        renderVagas();
    }

    // ==========================================================================
    // 3. LÓGICA DA PÁGINA DE LOGIN (login.html)
    // ==========================================================================
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const email = document.getElementById('email').value;
            const password = document.getElementById('password').value;
            const btnLogin = document.getElementById('btnLogin');
            btnLogin.disabled = true;
            btnLogin.textContent = 'Autenticando...';

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, senha: password })
                });
                const data = await res.json();
                if (data.success) {
                    localStorage.setItem('user_nome', data.nome);
                    window.location.href = '/home';
                } else {
                    alert(data.message || 'Acesso negado.');
                    btnLogin.disabled = false;
                    btnLogin.textContent = 'Entrar';
                }
            } catch (error) {
                alert('Servidor indisponível.');
                btnLogin.disabled = false;
                btnLogin.textContent = 'Entrar';
            }
        });
    }

    // ==========================================================================
    // 4. LÓGICA DA DASHBOARD (dashboard.html)
    // ==========================================================================
    const dashboardContainer = document.querySelector('.dashboard-grid');
    if (dashboardContainer) {
        async function fetchDashboardData() {
            try {
                const res = await fetch('/dashboard_data');
                if (!res.ok) throw new Error(`Status API: ${res.status}`);
                const data = await res.json();
                if (!data) return;

                document.getElementById('totalCandidatos').textContent = data.total_candidatos || 0;
                document.getElementById('mediaPontuacao').textContent = data.media_pontuacao ? `${data.media_pontuacao}%` : '0%';

                const habilidadesCtx = document.getElementById('habilidadesChart');
                if (habilidadesCtx && data.habilidades_mais_comuns) {
                    new Chart(habilidadesCtx, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(data.habilidades_mais_comuns),
                            datasets: [{
                                label: 'Ocorrências',
                                data: Object.values(data.habilidades_mais_comuns),
                                backgroundColor: '#38bdf8',
                                borderRadius: 4
                            }]
                        },
                        options: { indexAxis: 'y', responsive: true, plugins: { legend: { display: false } } }
                    });
                }

                const pontuacaoCtx = document.getElementById('pontuacaoChart');
                if (pontuacaoCtx && data.distribuicao_pontuacoes) {
                    new Chart(pontuacaoCtx, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(data.distribuicao_pontuacoes),
                            datasets: [{
                                label: 'Candidatos',
                                data: Object.values(data.distribuicao_pontuacoes),
                                backgroundColor: '#10b981',
                                borderRadius: 4
                            }]
                        },
                        options: { responsive: true, plugins: { legend: { display: false } } }
                    });
                }

                const formacoesList = document.getElementById('topFormacoes');
                if (formacoesList && data.formacoes_mais_comuns) {
                    formacoesList.innerHTML = Object.entries(data.formacoes_mais_comuns)
                        .map(([formacao, count]) => `<li style="display:flex; justify-content:space-between; margin-bottom:0.5rem; padding-bottom:0.5rem; border-bottom:1px solid var(--border-color);"><span>${formacao}</span> <strong>${count}</strong></li>`)
                        .join('');
                }
            } catch (error) {
                console.error("Falha ao carregar Dashboard:", error);
            }
        }
        fetchDashboardData();
    }

    // ==========================================================================
    // 5. LÓGICA DA PÁGINA DE UPLOAD (upload.html)
    // ==========================================================================
    const uploadForm = document.getElementById('uploadForm');
    if (uploadForm) {
        const btnIniciar = document.getElementById('btnIniciarTriagemUpload');
        const fileInput = document.getElementById('arquivo');
        
        uploadForm.addEventListener('submit', (event) => {
            if (fileInput.files.length === 0) {
                alert("Insira pelo menos um currículo (PDF ou DOCX).");
                event.preventDefault();
                return;
            }
            if (btnIniciar) {
                btnIniciar.disabled = true;
                btnIniciar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando (IA em execução)...';
            }
        });

        const fileDisplay = document.getElementById('arquivosSelecionados');
        const dragDropArea = document.getElementById('dragDropArea');
        
        if(fileInput && fileDisplay && dragDropArea){
            document.getElementById('btnSelecionarArquivos').addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', () => updateFileDisplay(fileInput.files));
    
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dragDropArea.addEventListener(eventName, e => { e.preventDefault(); e.stopPropagation(); });
            });
            
            ['dragenter', 'dragover'].forEach(eventName => dragDropArea.addEventListener(eventName, () => dragDropArea.classList.add('dragover')));
            ['dragleave', 'drop'].forEach(eventName => dragDropArea.addEventListener(eventName, () => dragDropArea.classList.remove('dragover')));
            
            dragDropArea.addEventListener('drop', e => {
                fileInput.files = e.dataTransfer.files;
                updateFileDisplay(fileInput.files);
            });
    
            function updateFileDisplay(files) {
                if (files.length > 0) {
                    fileDisplay.innerHTML = `<strong style="color:var(--secondary-color);">${files.length} arquivo(s) na fila.</strong>`;
                } else {
                    fileDisplay.textContent = 'Arraste e solte os arquivos aqui';
                }
            }
        }
    }

    // ==========================================================================
    // 6. LÓGICA DA PÁGINA DE DETALHES DO CANDIDATO (candidate_details.html)
    // ==========================================================================
    const tabsContainer = document.querySelector('.tabs-navigation');
    if (tabsContainer) {
        const tabButtons = tabsContainer.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTabId = button.dataset.tab;
                
                tabButtons.forEach(btn => btn.classList.remove('active'));
                button.classList.add('active');
                
                tabContents.forEach(content => {
                    content.classList.remove('active');
                    if (content.id === `tab${targetTabId.charAt(0).toUpperCase() + targetTabId.slice(1)}`) {
                        content.classList.add('active');
                    }
                });
            });
        });
        
        if(tabButtons.length > 0) tabButtons[0].click();
    }

    // ==========================================================================
    // 7. LÓGICA DA PÁGINA DE CANDIDATOS (candidatos_ranqueados.html)
    // ==========================================================================
    const candidateListContainer = document.getElementById('candidateList');
    if (candidateListContainer) {
        const vagaSelector = document.getElementById('vagaSelector');
        const optionsModal = document.getElementById('candidateOptionsModal');
        const modalCandidateName = document.getElementById('modalCandidateName');
        const btnCloseModal = optionsModal ? optionsModal.querySelector('.close-button') : null;
        const btnReprove = document.getElementById('btnReproveCandidate');
        const btnDelete = document.getElementById('btnDeleteCandidate');
        const btnCancel = document.getElementById('btnCancelOption');
        let currentCandidateId = null;

        function renderCandidates(candidates) {
            candidateListContainer.innerHTML = '';
            if (!candidates || candidates.length === 0) {
                candidateListContainer.innerHTML = '<p style="text-align:center; padding:2rem; color:var(--text-muted);">Nenhum talento encontrado no banco.</p>';
                return;
            }

            candidates.forEach((c, index) => {
                const item = document.createElement('div');
                item.className = 'card';
                item.style.display = 'flex';
                item.style.alignItems = 'center';
                item.style.gap = '1.5rem';
                item.style.padding = '1rem 1.5rem';

                let rankHTML = '';
                let tierHTML = '';
                
                if (c.nivel) {
                    let color = c.nivel === 'Excelente' ? 'var(--success-color)' : (c.nivel === 'Promissor' ? 'var(--secondary-color)' : 'var(--text-muted)');
                    tierHTML = `<span style="background-color:${color}; color:white; padding:4px 12px; border-radius:20px; font-weight:600; font-size:0.85rem;">${c.nivel}</span>`;
                } else {
                    tierHTML = `<span style="font-weight:700; color:var(--text-muted);">${c.pontuacao}% Score</span>`;
                }

                if (c.indice_adequacao !== undefined) { 
                    let color = index === 0 ? '#fbbf24' : (index === 1 ? '#9ca3af' : (index === 2 ? '#b45309' : 'transparent'));
                    let rankText = index < 3 ? '<i class="fas fa-trophy"></i>' : `${index + 1}º`;
                    rankHTML = `<div style="font-size:1.2rem; font-weight:bold; color:${color}; width:40px; text-align:center;">${rankText}</div>`;
                }

                item.id = `candidato-item-${c.id}`;
                item.innerHTML = `
                    ${rankHTML}
                    <div style="flex-grow:1;">
                        <h4 style="margin:0; font-size:1.1rem; color:var(--primary-color);">${c.nome}</h4>
                        <small style="color:var(--text-muted);">${c.email || 'Sem e-mail'}</small>
                    </div>
                    ${tierHTML}
                    <div style="display:flex; gap:0.5rem;">
                        <a href="/detalhes_candidato/${c.id}" class="btn btn-secondary btn-sm" style="padding:0.4rem 0.8rem;">Perfil</a>
                        <button class="btn btn-secondary btn-sm btn-options" data-id="${c.id}" data-name="${c.nome}" style="padding:0.4rem 0.8rem;"><i class="fas fa-ellipsis-v"></i></button>
                    </div>
                `;
                candidateListContainer.appendChild(item);
            });
        }

        function openOptionsModal(id, name) {
            currentCandidateId = id;
            if(modalCandidateName) modalCandidateName.textContent = name;
            if(optionsModal) optionsModal.style.display = 'flex';
        }

        function closeOptionsModal() {
            if(optionsModal) optionsModal.style.display = 'none';
            currentCandidateId = null;
        }

        candidateListContainer.addEventListener('click', (e) => {
            const optionsButton = e.target.closest('.btn-options');
            if (optionsButton) {
                openOptionsModal(optionsButton.dataset.id, optionsButton.dataset.name);
            }
        });

        if (btnCloseModal) btnCloseModal.onclick = closeOptionsModal;
        if (btnCancel) btnCancel.onclick = closeOptionsModal;

        if (btnReprove) {
            btnReprove.addEventListener('click', async () => {
                if (!currentCandidateId) return;
                const res = await fetch(`/api/candidatos/${currentCandidateId}/reprovar`, { method: 'POST' });
                if (res.ok) {
                    document.getElementById(`candidato-item-${currentCandidateId}`).remove();
                    closeOptionsModal();
                } else { alert('Erro no servidor.'); }
            });
        }

        if (btnDelete) {
            btnDelete.addEventListener('click', async () => {
                if (!currentCandidateId) return;
                if (confirm('Aviso: Exclusão permanente do banco de dados.')) {
                    const res = await fetch(`/api/candidatos/${currentCandidateId}`, { method: 'DELETE' });
                    if (res.ok) {
                        document.getElementById(`candidato-item-${currentCandidateId}`).remove();
                        closeOptionsModal();
                    } else { alert('Erro de exclusão.'); }
                }
            });
        }
        
        async function atualizarListaPorVaga() {
            const vagaId = vagaSelector.value;
            if (vagaId === 'geral') {
                renderCandidates(window.FLASK_CANDIDATES_DATA || []);
                return;
            }
            candidateListContainer.innerHTML = '<p style="text-align:center; padding:2rem;"><i class="fas fa-sync fa-spin"></i> Processando Match Algorítmico...</p>';
            try {
                const res = await fetch(`/candidatos_ranqueados?vaga_id=${vagaId}`);
                const data = await res.json();
                renderCandidates(data);
            } catch (error) {
                candidateListContainer.innerHTML = '<p style="text-align:center; color:var(--danger-color);">Falha na comunicação com o algoritmo de rankeamento.</p>';
            }
        }

        if(vagaSelector) vagaSelector.addEventListener('change', atualizarListaPorVaga);
        renderCandidates(window.FLASK_CANDIDATES_DATA || []);
    }

    // ==========================================================================
    // 8. LÓGICA DA PÁGINA DE AGENDAMENTO (agendar_entrevista.html)
    // ==========================================================================
    const interviewForm = document.getElementById('interviewForm');
    if (interviewForm) {
        interviewForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const btnConfirmar = document.getElementById('btnConfirmarAgendamento');
            btnConfirmar.disabled = true;
            btnConfirmar.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Registrando...';

            const interviewData = {
                candidato_id: interviewForm.dataset.candidateId,
                candidato_nome: interviewForm.dataset.candidateName,
                tipo: document.getElementById('tipoEntrevista').value,
                recrutador: document.getElementById('recrutador').value,
                data: document.getElementById('dataEntrevista').value,
                hora: document.getElementById('horaEntrevista').value
            };

            try {
                const res = await fetch('/api/agendar_entrevista', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(interviewData)
                });
                const data = await res.json();
                if (data.success) {
                    window.location.href = `/detalhes_candidato/${interviewData.candidato_id}`;
                } else {
                    alert('Falha ao registrar agendamento.');
                    btnConfirmar.disabled = false;
                    btnConfirmar.textContent = 'Confirmar agendamento';
                }
            } catch (error) {
                alert('Erro interno do servidor.');
                btnConfirmar.disabled = false;
                btnConfirmar.textContent = 'Confirmar agendamento';
            }
        });
    }
});
