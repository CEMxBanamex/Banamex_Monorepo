"""bloquear set_config para el usuario de consultas

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09 17:30:00

Un SELECT como `SELECT set_config('app.rol', 'administrador', true), * FROM v_clientes` cambia el rol dentro
de la transacción y se salta la seguridad por fila y el enmascaramiento. Validar que sea un solo SELECT no lo evita.
Se quita set_config a PUBLIC (en esta base) y se deja solo a quien la necesita. El contexto se fija con SET LOCAL,
que no depende de este permiso.
"""
from alembic import op

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
DO $$
DECLARE r text;
BEGIN
  REVOKE EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) FROM PUBLIC;
  -- Quien migra (en RDS, el usuario maestro no es superusuario) la conserva para pg_dump y mantenimiento.
  EXECUTE format('GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) TO %I', current_user);
  FOREACH r IN ARRAY ARRAY['steward_backend', 'steward_mcp'] LOOP
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
      EXECUTE format('GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) TO %I', r);
    END IF;
  END LOOP;
  -- Si quien migra no es dueño de la función (posible en RDS), REVOKE no falla: solo no hace nada. Por eso se verifica.
  -- No se rompe el despliegue, pero queda solo la defensa de la validación del SQL en ejecutar_consulta.
  IF EXISTS (SELECT 1 FROM pg_proc p, aclexplode(coalesce(p.proacl, acldefault('f', p.proowner))) a
             WHERE p.oid = 'pg_catalog.set_config(text,text,boolean)'::regprocedure
               AND a.grantee = 0 AND a.privilege_type = 'EXECUTE') THEN
    RAISE WARNING 'set_config sigue disponible para PUBLIC: el usuario de consultas puede saltarse la seguridad por fila. '
                  'Pide a un superusuario: REVOKE EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) FROM PUBLIC';
  END IF;
END $$;
""")


def downgrade():
    op.execute("GRANT EXECUTE ON FUNCTION pg_catalog.set_config(text, text, boolean) TO PUBLIC")
