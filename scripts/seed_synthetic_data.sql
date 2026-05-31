-- =====================================================================
-- Dados sintéticos para o BI (Metabase) — Sistema RAG Cancella
-- Popula users, documents e conversation_logs com dados realistas.
-- Idempotente: limpa os dados sintéticos antes de reinserir.
-- Rodar:  docker compose exec -T db psql -U rag -d ragdb -f - < scripts/seed_synthetic_data.sql
-- =====================================================================

BEGIN;

-- Limpa dados anteriores (apenas dados de seed) ----------------------
DELETE FROM conversation_logs;
DELETE FROM documents WHERE id LIKE 'doc0%';
DELETE FROM users WHERE id LIKE 'usr0%';

-- Usuários (clientes B2B + admin) ------------------------------------
INSERT INTO users (id, email, hashed_password, role, is_active, created_at) VALUES
  ('usr01', 'ti@datacorp.com.br',        'x', 'user',  true, now() - interval '90 days'),
  ('usr02', 'suporte@nexustech.com.br',  'x', 'user',  true, now() - interval '85 days'),
  ('usr03', 'infra@alphasys.com.br',     'x', 'user',  true, now() - interval '80 days'),
  ('usr04', 'redes@betaservicos.com.br', 'x', 'user',  true, now() - interval '70 days'),
  ('usr05', 'admin@gammanet.com.br',     'x', 'user',  true, now() - interval '60 days'),
  ('usr06', 'helpdesk@deltacorp.com.br', 'x', 'user',  true, now() - interval '55 days'),
  ('usr07', 'operacoes@epsilon.com.br',  'x', 'user',  true, now() - interval '40 days'),
  ('usr08', 'admin@cancella.com.br',     'x', 'admin', true, now() - interval '120 days');

-- Documentos (manuais técnicos) --------------------------------------
INSERT INTO documents (id, filename, original_path, status, created_at, updated_at) VALUES
  ('doc01', 'manual_poweredge_r740_hw.pdf',   '/app/storage/pdfs/manual_poweredge_r740_hw.pdf',   'ready', now() - interval '100 days', now()),
  ('doc02', 'guia_firewall_fortinet.pdf',     '/app/storage/pdfs/guia_firewall_fortinet.pdf',     'ready', now() - interval '100 days', now()),
  ('doc03', 'manual_switch_cisco_2960.pdf',   '/app/storage/pdfs/manual_switch_cisco_2960.pdf',   'ready', now() - interval '95 days',  now()),
  ('doc04', 'backup_veeam_procedimentos.pdf', '/app/storage/pdfs/backup_veeam_procedimentos.pdf', 'ready', now() - interval '90 days',  now()),
  ('doc05', 'config_vpn_ipsec.pdf',           '/app/storage/pdfs/config_vpn_ipsec.pdf',           'ready', now() - interval '85 days',  now()),
  ('doc06', 'manual_nobreak_apc_smart.pdf',   '/app/storage/pdfs/manual_nobreak_apc_smart.pdf',   'ready', now() - interval '80 days',  now()),
  ('doc07', 'windows_server_2022_ad.pdf',     '/app/storage/pdfs/windows_server_2022_ad.pdf',     'ready', now() - interval '75 days',  now()),
  ('doc08', 'storage_nas_synology.pdf',       '/app/storage/pdfs/storage_nas_synology.pdf',       'ready', now() - interval '70 days',  now());

-- Conversas ----------------------------------------------------------
-- Catálogo de tópicos (pergunta, resposta, documento de origem)
WITH topics AS (
  SELECT * FROM (VALUES
    (1, 'O servidor Dell PowerEdge R740 não reconhece o disco no slot 3. O que verificar?',
        'Conforme o Manual de Hardware Dell PowerEdge R740 (seção 4.2): verifique o cabo SAS/SATA no backplane, o status do controlador PERC H730P no iDRAC em Storage → Physical Disks, e execute "Import Foreign Configuration" caso o disco apareça como Foreign.',
        'doc01', 'manual_poweredge_r740_hw.pdf'),
    (2, 'Como liberar a porta 443 no firewall Fortinet?',
        'No FortiGate, vá em Policy & Objects → Firewall Policy → Create New, defina o serviço HTTPS (443), origem/destino e Action = ACCEPT. Salve e mova a regra acima das regras de bloqueio.',
        'doc02', 'guia_firewall_fortinet.pdf'),
    (3, 'O switch Cisco 2960 está com uma porta em estado err-disabled. Como reabilitar?',
        'A porta entrou em err-disabled, geralmente por port-security ou BPDU guard. Identifique a causa com "show interface status err-disabled", remova o problema e reabilite com "shutdown" seguido de "no shutdown" na interface.',
        'doc03', 'manual_switch_cisco_2960.pdf'),
    (4, 'O job de backup no Veeam falhou com erro de VSS. O que fazer?',
        'Erros de VSS no Veeam costumam vir de writers travados. Rode "vssadmin list writers" no host, reinicie os serviços com estado de erro e verifique espaço livre no volume de snapshot antes de reexecutar o job.',
        'doc04', 'backup_veeam_procedimentos.pdf'),
    (5, 'Como configurar um túnel VPN IPSec site-to-site?',
        'Defina as fases IKE: Fase 1 (autenticação, DH group, lifetime) e Fase 2 (proposta IPSec, PFS). Garanta que os parâmetros e a pre-shared key coincidam nos dois lados e que as sub-redes interessantes estejam corretas.',
        'doc05', 'config_vpn_ipsec.pdf'),
    (6, 'O nobreak APC Smart-UPS está apitando continuamente. O que significa?',
        'O bipe contínuo indica operação em bateria (queda de energia) ou bateria com defeito. Verifique a energia da rede, o status no display e, se persistir, faça o teste de autodiagnóstico segurando o botão por ~2 segundos.',
        'doc06', 'manual_nobreak_apc_smart.pdf'),
    (7, 'Como promover um servidor Windows Server 2022 a controlador de domínio?',
        'Instale a role AD DS via Server Manager, depois use "Promote this server to a domain controller". Escolha adicionar a uma floresta existente ou criar nova, defina o nível funcional e o DSRM password.',
        'doc07', 'windows_server_2022_ad.pdf'),
    (8, 'O NAS Synology não está acessível pela rede. Como diagnosticar?',
        'Verifique o LED de status e de rede no equipamento, confirme o IP via Synology Assistant, teste o ping e cheque se os serviços SMB/AFP estão habilitados em Painel de Controle → Serviços de Arquivo.',
        'doc08', 'storage_nas_synology.pdf'),
    (9, 'Qual a sequência correta de inicialização após uma queda de energia no rack?',
        'Ligue primeiro o nobreak e aguarde estabilizar, depois o storage/NAS, em seguida os switches e por último os servidores, garantindo que as dependências de rede e disco estejam disponíveis antes da subida das aplicações.',
        'doc01', 'manual_poweredge_r740_hw.pdf'),
    (10, 'Como verificar logs de erro de hardware no iDRAC?',
        'Acesse o iDRAC pela interface web, vá em Maintenance → System Event Log (SEL) para ver eventos de hardware, ou use Logs → Lifecycle Log para um histórico mais completo de falhas e alterações.',
        'doc01', 'manual_poweredge_r740_hw.pdf'),
    (11, 'Como criar uma regra de NAT no Fortinet para um servidor web interno?',
        'Crie um VIP (Virtual IP) mapeando o IP externo para o IP interno do servidor em Policy & Objects → Virtual IPs, e depois uma policy de entrada usando esse VIP como destino com o serviço desejado.',
        'doc02', 'guia_firewall_fortinet.pdf'),
    (12, 'O cliente reclama de lentidão na VLAN de produção do switch Cisco. Como investigar?',
        'Use "show interfaces" para checar erros/CRC e utilização, "show mac address-table" para mapear hosts e verifique se há loops ou negociação de duplex incorreta nas portas de uplink.',
        'doc03', 'manual_switch_cisco_2960.pdf')
  ) AS t(tid, question, answer, doc_id, filename)
),
n AS (SELECT count(*)::int AS c FROM topics),
-- Sessões: cada uma com um usuário, uma data base e de 1 a 4 mensagens
sessions AS (
  SELECT
    gen_random_uuid()::text AS session_id,
    (ARRAY['usr01','usr02','usr03','usr04','usr05','usr06','usr07'])[1 + floor(random()*7)::int] AS user_id,
    now() - (random() * interval '60 days') AS base_ts,
    1 + floor(random()*4)::int AS n_msgs
  FROM generate_series(1, 260)
),
-- Expande cada sessão em mensagens
msgs AS (
  SELECT
    s.session_id,
    s.user_id,
    s.base_ts + ((m - 1) * interval '80 seconds') AS ts,
    1 + floor(random() * (SELECT c FROM n))::int AS tid,
    random() AS r_nf,       -- chance de "não encontrado"
    random() AS r_hasrate,  -- chance de ter recebido feedback
    random() AS r_rate,     -- positivo vs negativo
    random() AS r_slow      -- chance de estourar SLA de 5s
  FROM sessions s, LATERAL generate_series(1, s.n_msgs) AS m
)
INSERT INTO conversation_logs
  (session_id, user_id, question, answer, source_document_id, source_filename,
   not_found, rating, response_time_ms, created_at)
SELECT
  msgs.session_id,
  msgs.user_id,
  t.question,
  CASE WHEN msgs.r_nf < 0.15
       THEN 'Não encontrei essa informação nos manuais técnicos disponíveis. Encaminhe a dúvida ao técnico responsável.'
       ELSE t.answer END,
  CASE WHEN msgs.r_nf < 0.15 THEN NULL ELSE t.doc_id END,
  CASE WHEN msgs.r_nf < 0.15 THEN NULL ELSE t.filename END,
  (msgs.r_nf < 0.15) AS not_found,
  -- Feedback: ~70% das respostas recebem rating. Quando "não encontrado",
  -- a satisfação cai; quando respondido, ~85% útil.
  CASE
    WHEN msgs.r_hasrate < 0.70 THEN
      CASE
        WHEN msgs.r_nf < 0.15 THEN (CASE WHEN msgs.r_rate < 0.55 THEN 'not_useful' ELSE 'useful' END)
        ELSE (CASE WHEN msgs.r_rate < 0.85 THEN 'useful' ELSE 'not_useful' END)
      END
    ELSE NULL
  END::feedback_rating,
  -- Tempo de resposta: ~90% entre 1,2s e 4,5s; ~10% estoura o SLA (5–9s)
  CASE
    WHEN msgs.r_slow < 0.10 THEN (5000 + floor(random()*4000))::int
    ELSE (1200 + floor(random()*3300))::int
  END AS response_time_ms,
  msgs.ts
FROM msgs
JOIN topics t ON t.tid = msgs.tid;

COMMIT;

-- Resumo do que foi inserido -----------------------------------------
SELECT
  (SELECT count(*) FROM conversation_logs)                          AS total_conversas,
  (SELECT count(DISTINCT session_id) FROM conversation_logs)        AS total_sessoes,
  (SELECT count(*) FROM conversation_logs WHERE not_found = false)  AS respondidas,
  (SELECT count(*) FROM conversation_logs WHERE rating = 'useful')  AS feedback_util,
  round((SELECT avg(response_time_ms) FROM conversation_logs))      AS tmpr_medio_ms;
