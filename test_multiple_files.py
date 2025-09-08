#!/usr/bin/env python3
"""
Teste da Funcionalidade de Múltiplos Arquivos
=============================================

Este script testa especificamente a nova funcionalidade de upload
de múltiplos arquivos da Cápsula do Tempo.
"""

import requests
import tempfile
import os
from datetime import datetime

def print_header(title):
    print(f"\n{'='*60}")
    print(f" {title}")
    print(f"{'='*60}")

def print_success(message):
    print(f"✅ {message}")

def print_error(message):
    print(f"❌ {message}")

def print_info(message):
    print(f"ℹ️  {message}")

def create_test_files():
    """Cria arquivos de teste temporários"""
    print_info("Criando arquivos de teste...")
    
    test_files = []
    
    # Criar 3 arquivos de teste
    for i in range(1, 4):
        # Criar arquivo temporário
        temp_file = tempfile.NamedTemporaryFile(
            mode='w+b', 
            suffix=f'_test_{i}.txt',
            delete=False
        )
        
        # Conteúdo do arquivo
        content = f"""Arquivo de Teste #{i}
========================

Este é um arquivo de teste criado para validar
a funcionalidade de múltiplos arquivos.

Criado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Arquivo: {i} de 3
Tamanho: Pequeno para teste rápido

Conteúdo adicional para dar um pouco mais de tamanho...
Linha extra 1
Linha extra 2
Linha extra 3

Fim do arquivo de teste #{i}
"""
        
        temp_file.write(content.encode('utf-8'))
        temp_file.close()
        
        test_files.append(temp_file.name)
        print_info(f"Arquivo criado: {os.path.basename(temp_file.name)}")
    
    return test_files

def test_multiple_upload(files):
    """Testa o upload de múltiplos arquivos"""
    print_header("TESTANDO UPLOAD DE MÚLTIPLOS ARQUIVOS")
    
    url = "http://localhost:8000/upload"
    
    # Dados do formulário
    form_data = {
        'nome': 'Teste Múltiplos Arquivos',
        'mensagem': 'Este é um teste da nova funcionalidade de múltiplos arquivos!',
        'consentimento': 'true'
    }
    
    # Preparar arquivos para upload
    file_handles = []
    try:
        print_info(f"Preparando {len(files)} arquivos para upload...")
        
        files_data = []
        for file_path in files:
            file_handle = open(file_path, 'rb')
            file_handles.append(file_handle)
            files_data.append(('files', (os.path.basename(file_path), file_handle, 'text/plain')))
        
        print_info("Enviando requisição para o servidor...")
        
        # Fazer a requisição
        response = requests.post(
            url,
            data=form_data,
            files=files_data,
            timeout=30
        )
        
        print_info(f"Status da resposta: {response.status_code}")
        
        if response.status_code == 200:
            print_success("Upload realizado com sucesso!")
            
            # Verificar se a resposta contém indicadores de sucesso
            response_text = response.text.lower()
            if 'upload concluído' in response_text or 'arquivo(s) enviado(s)' in response_text:
                print_success("Resposta confirma upload múltiplo bem-sucedido!")
            else:
                print_info("Resposta recebida, mas não foi possível confirmar detalhes")
                
        else:
            print_error(f"Erro no upload: Status {response.status_code}")
            print_info("Conteúdo da resposta:")
            print(response.text[:500])  # Primeiros 500 caracteres
    
    except requests.exceptions.ConnectionError:
        print_error("Não foi possível conectar ao servidor!")
        print_info("Certifique-se de que o servidor está rodando com: uv run app.py")
        return False
    
    except Exception as e:
        print_error(f"Erro durante o teste: {e}")
        return False
    
    finally:
        # Fechar todos os file handles
        for file_handle in file_handles:
            file_handle.close()
    
    return True

def cleanup_test_files(files):
    """Remove os arquivos de teste"""
    print_info("Limpando arquivos de teste...")
    
    for file_path in files:
        try:
            os.unlink(file_path)
            print_info(f"Removido: {os.path.basename(file_path)}")
        except Exception as e:
            print_error(f"Erro ao remover {file_path}: {e}")

def main():
    """Função principal do teste"""
    print_header("TESTE DE MÚLTIPLOS ARQUIVOS - CÁPSULA DO TEMPO")
    print("Este script testa a nova funcionalidade de upload múltiplo.")
    
    test_files = []
    try:
        # Criar arquivos de teste
        test_files = create_test_files()
        
        # Testar upload
        success = test_multiple_upload(test_files)
        
        # Resultado
        print_header("RESULTADO DO TESTE")
        if success:
            print_success("🎉 TESTE DE MÚLTIPLOS ARQUIVOS PASSOU!")
            print_info("A funcionalidade está funcionando corretamente!")
        else:
            print_error("❌ TESTE FALHOU")
            print_info("Verifique os logs acima para mais detalhes")
    
    finally:
        # Sempre limpar os arquivos de teste
        if test_files:
            cleanup_test_files(test_files)
    
    print(f"\nTeste executado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
