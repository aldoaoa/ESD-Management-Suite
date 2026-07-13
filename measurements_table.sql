-- Script para crear la tabla measurements en Supabase (PostgreSQL)

CREATE TABLE IF NOT EXISTS public.measurements (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    site_id UUID NOT NULL,
    asset_id UUID NOT NULL,
    auditor_id UUID NOT NULL,
    temperatura NUMERIC,
    humedad NUMERIC,
    resistance_value NUMERIC,
    static_field_value NUMERIC,
    status_result TEXT NOT NULL,
    observaciones TEXT,
    extra_data JSONB, -- Almacena detalles de Validación Integral (Ej: {"m1": 1.5e6, "m2": ...})
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Si deseas crear índices para optimizar las consultas:
CREATE INDEX IF NOT EXISTS idx_measurements_site_id ON public.measurements(site_id);
CREATE INDEX IF NOT EXISTS idx_measurements_asset_id ON public.measurements(asset_id);
CREATE INDEX IF NOT EXISTS idx_measurements_measured_at ON public.measurements(measured_at DESC);

-- Opcional: Relaciones de llave foránea (si tienes las tablas sites, assets, users)
-- ALTER TABLE public.measurements ADD CONSTRAINT fk_measurements_site FOREIGN KEY (site_id) REFERENCES public.sites(id) ON DELETE CASCADE;
-- ALTER TABLE public.measurements ADD CONSTRAINT fk_measurements_asset FOREIGN KEY (asset_id) REFERENCES public.assets(id) ON DELETE CASCADE;
-- ALTER TABLE public.measurements ADD CONSTRAINT fk_measurements_auditor FOREIGN KEY (auditor_id) REFERENCES public.users(id) ON DELETE SET NULL;
